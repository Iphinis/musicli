"""player.py"""

import subprocess
import socket
import json
import os
import signal
import time
import json
import socket
import threading
from typing import Optional, Callable

from settings import Settings

def _new_process_group():
    """Ensure the child starts in a new process group (Unix)."""
    try:
        os.setpgrp()
    except Exception:
        pass

class Player:
    def __init__(
        self,
        player_cmd: str = Settings.get('player', 'player_cmd'),
        ipc_socket: str = Settings.get('player', 'ipc_path'),
        enable_ipc: bool = True,
        disable_video: bool = False,
        socket_timeout: float = 5.0,
        socket_poll_interval: float = 0.05
    ):
        """
        Media player controller that spawns a fresh MPV for each play,
        with reliable IPC socket detection without fixed sleeps.

        Args:
            player_cmd: MPV command or path.
            ipc_socket: UNIX socket path for IPC.
            enable_ipc: Whether to start in IPC mode.
            disable_video: Pass --no-video to MPV.
            socket_timeout: Max seconds to wait for IPC socket creation.
            socket_poll_interval: Seconds between socket existence polls.
        """
        self.player_cmd = player_cmd
        self.ipc_socket = ipc_socket
        self.enable_ipc = enable_ipc
        self.disable_video = disable_video
        self.process = None
        self.socket_timeout = socket_timeout
        self.socket_poll_interval = socket_poll_interval

        # Event / property thread + state
        self._event_thread: Optional[threading.Thread] = None
        self._event_thread_stop = threading.Event()
        self._props_lock = threading.Lock()
        self._props_cv = threading.Condition(self._props_lock)

        # properties we track: 'playlist-count' and 'playlist-pos' (kept as ints or None)
        self._props = {"playlist-count": 0, "playlist-pos": None}

        # optional external callback for every mpv event (useful for debugging)
        self._event_callback: Optional[Callable[[dict], None]] = None

        if self.enable_ipc:
            self._cleanup_socket()

    # -------------------------
    # process & command helpers
    # -------------------------
    def _cleanup_socket(self):
        try:
            os.remove(self.ipc_socket)
        except OSError:
            pass

    def _build_cmd(self, target:str) -> list:
        cmd = [
            self.player_cmd,
            "--force-window=yes",
            "--really-quiet",
        ]
        if self.enable_ipc:
            cmd.append(f"--input-ipc-server={self.ipc_socket}")
            cmd.append("--idle=yes")
        else:
            cmd.append("--keep-open=yes")
        
        if self.disable_video:
            cmd.append("--video=no")
        
        if target:
            cmd.append(target)

        return cmd

    def _start_process(self, target: str):
        """Spawn MPV, then wait for the IPC socket to appear."""
        # Tear down any existing player
        self.stop()
        cmd = self._build_cmd(target)

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=_new_process_group
        )

        if self.enable_ipc:
            self._wait_for_socket()
            self._ensure_event_thread_and_observers()

    def _wait_for_socket(self):
        """Wait up to socket_timeout for the IPC socket file."""
        deadline = time.monotonic() + self.socket_timeout
        while time.monotonic() < deadline:
            if os.path.exists(self.ipc_socket):
                return
            time.sleep(self.socket_poll_interval)
        raise TimeoutError(f"IPC socket not created within {self.socket_timeout}s")

    def _send_command(self, command: list):
        if not self.enable_ipc or not self.process:
            return
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(self.ipc_socket)
                payload = json.dumps({"command": command}) + "\n"
                sock.sendall(payload.encode('utf-8'))
        except Exception:
            # Could log or retry here if needed
            pass

    # -------------------------
    # low-level IPC send/request
    # -------------------------
    def _open_ipc(self, timeout=None):
        """Return a connected UNIX socket. Caller must close it (use with)."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout or self.socket_timeout)
        sock.connect(self.ipc_socket)
        return sock

    def ipc_send(self, command: list) -> None:
        """
        Fire-and-forget: send a JSON IPC command (no reply required).
        Safe to call whether mpv is running or not (it will silently return).
        """
        if not self.enable_ipc or not self.process:
            return
        try:
            with self._open_ipc() as sock:
                payload = json.dumps({"command": command}) + "\n"
                sock.sendall(payload.encode("utf-8"))
        except Exception:
            # ignore; caller can fallback / detect via properties
            pass

    def ipc_request(self, command:list, timeout:float|None=None) -> dict|None:
        """
        Send a JSON IPC command and return the parsed JSON reply (dict), or None on error.
        Blocks until one JSON line is returned or socket timeout.
        """
        if not self.enable_ipc or not self.process:
            return None
        try:
            with self._open_ipc(timeout) as sock:
                payload = json.dumps({"command": command}) + "\n"
                sock.sendall(payload.encode("utf-8"))

                # read until newline then parse JSON
                data = bytearray()
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    data.extend(chunk)
                    if data.endswith(b"\n"):
                        break
                if not data:
                    return None
                # mpv replies may send multiple lines; parse the first complete JSON object
                line = data.splitlines()[0].decode("utf-8", errors="ignore").strip()
                return json.loads(line)
        except Exception:
            return None

    # -------------------------
    # property helpers + waiting
    # -------------------------
    def get_property(self, name: str):
        """Get a property via IPC (returns data or None)."""
        resp = self.ipc_request(["get_property", name])
        if not resp:
            return None
        if resp.get("error") == "success":
            return resp.get("data")
        return None

    def _update_prop(self, name: str, value):
        """Internal: update cached prop and notify waiters if value changed."""
        with self._props_cv:
            prev = self._props.get(name)
            # normalize int when appropriate
            new = None
            try:
                if value is None:
                    new = None
                else:
                    if name == "playlist-count":
                        new = int(value)
                    elif name == "playlist-pos":
                        new = int(value)
                    else:
                        new = value
            except Exception:
                new = value
            if prev != new:
                self._props[name] = new
                # notify waiters
                self._props_cv.notify_all()

    def wait_for_playlist_count(self, expected_count:int, timeout:float=3) -> bool:
        """
        Wait until mpv reports playlist-count >= expected_count.
        Returns True if condition met, False on timeout.
        """
        deadline = time.monotonic() + timeout
        with self._props_cv:
            while time.monotonic() < deadline:
                current = self._props.get("playlist-count", 0)

                if current >= expected_count:
                    return True
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._props_cv.wait(timeout=min(0.2, remaining))
            return False

    # -------------------------
    # event thread & observation
    # -------------------------
    def _ensure_event_thread_and_observers(self):
        """Start event thread if missing and request observe_property for props."""
        # start event thread
        if self._event_thread is None or not self._event_thread.is_alive():
            self._event_thread_stop.clear()
            self._event_thread = threading.Thread(target=self._event_loop, daemon=True)
            self._event_thread.start()
            # give it a small moment to connect and subscribe
            time.sleep(0.05)

    def start_event_loop(self, callback: Optional[Callable[[dict], None]] = None):
        """
        Public: set an external callback for every mpv event and ensure thread running.
        callback(event_dict) will be called for each parsed JSON event.
        """
        self._event_callback = callback
        if self.process and self.enable_ipc:
            self._ensure_event_thread_and_observers()

    def _event_loop(self):
        """
        Connect to mpv IPC socket and continuously receive newline-delimited JSON events.
        We also send observe_property commands on connect so property-change arrives.
        """
        # keep trying until told to stop
        while not self._event_thread_stop.is_set():
            try:
                with self._open_ipc(timeout=None) as sock:
                    # on connect request observes for playlist-count and playlist-pos
                    # choose arbitrary request ids
                    sock.sendall((json.dumps({"command":["observe_property", 1, "playlist-count"]}) + "\n").encode("utf-8"))
                    sock.sendall((json.dumps({"command":["observe_property", 2, "playlist-pos"]}) + "\n").encode("utf-8"))
                    # read loop
                    buf = bytearray()
                    while not self._event_thread_stop.is_set():
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        buf.extend(chunk)
                        while b"\n" in buf:
                            line, _, rest = buf.partition(b"\n")
                            buf = bytearray(rest)
                            if not line:
                                continue
                            try:
                                obj = json.loads(line.decode("utf-8", errors="ignore"))
                            except Exception:
                                continue
                            # optional external callback for debugging
                            try:
                                if self._event_callback:
                                    try:
                                        self._event_callback(obj)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            # handle property-change events
                            if obj.get("event") == "property-change":
                                name = obj.get("name")
                                if name:
                                    self._update_prop(name, obj.get("data"))
                            elif obj.get("event") == "start-file":
                                # start-file often contains playlist-pos
                                pos = obj.get("playlist-pos")
                                if pos is not None:
                                    self._update_prop("playlist-pos", pos)
                                # also refresh playlist-count from mpv
                                pc = self.get_property("playlist-count")
                                if pc is not None:
                                    self._update_prop("playlist-count", pc)
                            elif obj.get("event") == "end-file":
                                # on end-file we don't mutate internal state here; event caller may use it
                                # but update playlist-count just in case
                                pc = self.get_property("playlist-count")
                                if pc is not None:
                                    self._update_prop("playlist-count", pc)
                            # other events ignored here
            except FileNotFoundError:
                # socket missing: wait and retry
                time.sleep(0.05)
            except ConnectionRefusedError:
                time.sleep(0.05)
            except Exception:
                # generic backoff to avoid tight loop
                time.sleep(0.1)
        # thread exit

    # -------------------------
    # high-level play helpers
    # -------------------------
    def is_playing(self) -> bool:
        """Return True if MPV process is running."""
        return bool(self.process and self.process.poll() is None)

    def start_idle(self):
        """Ensure mpv is running and in idle mode (no file loaded)."""
        if not self.is_playing():
            # start mpv in idle mode
            self._start_process(target=None)

    def play_track(self, filepath:str) -> None:
        """Load or reload a local file. If enable_ipc: send loadfile replace (starting mpv if necessary)."""
        if self.enable_ipc:
            if not self.is_playing():
                # start mpv idle then load
                self.start_idle()

                # wait up to socket timeout for playlist to initialize (some mpv versions)
                self.wait_for_playlist_count(0, timeout=1.0)

                # request loadfile replace
                self.ipc_send(["loadfile", filepath, "replace"])
            else:
                self.ipc_send(["loadfile", filepath, "replace"])
        else:
            subprocess.Popen(self._build_cmd(filepath), preexec_fn=_new_process_group if os.name != "nt" else None)


    def play_url(self, url:str) -> None:
        """Stream or reload a URL."""
        self.play_track(url)

    def stop(self) -> None:
        """Terminate MPV and clean up socket and event thread."""
        # signal event thread to stop first
        self._event_thread_stop.set()
        if self._event_thread and self._event_thread.is_alive():
            # give the thread a small chance to exit
            time.sleep(0.05)

        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception:
                try:
                    self.process.terminate()
                except Exception:
                    pass
            try:
                self.process.wait(timeout=1.0)
            except Exception:
                pass
            self.process = None

        if self.enable_ipc:
            self._cleanup_socket()

    def toggle_pause(self) -> None:
        """Toggle play/pause via IPC."""
        self._send_command(["cycle", "pause"])
