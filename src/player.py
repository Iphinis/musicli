import subprocess
import socket
import json
import os
import signal
import time


def _new_process_group():
    """Ensure the child starts in a new process group."""
    os.setpgrp()

class Player:
    def __init__(
        self,
        player_cmd: str = "mpv",
        ipc_socket: str = "/tmp/music-player-cli-socket",
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

        if self.enable_ipc:
            self._cleanup_socket()

    def _cleanup_socket(self):
        try:
            os.remove(self.ipc_socket)
        except OSError:
            pass

    def _build_cmd(self, target: str) -> list:
        cmd = [self.player_cmd, "--force-window=yes"]
        if self.enable_ipc:
            cmd.append(f"--input-ipc-server={self.ipc_socket}")
        if self.disable_video:
            cmd.append("--no-video")
        cmd.append(target)
        return cmd

    def _start_process(self, target: str):
        """Spawn MPV, then wait for the IPC socket to appear."""
        # Tear down any existing player
        self.stop()
        cmd = self._build_cmd(target)
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=_new_process_group
        )
        if self.enable_ipc:
            self._wait_for_socket()

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

    def is_playing(self) -> bool:
        """Return True if MPV process is running."""
        return bool(self.process and self.process.poll() is None)

    def play_track(self, filepath: str) -> None:
        """Load or reload a local file."""
        if self.enable_ipc:
            if not self.is_playing():
                self._start_process(filepath)
            else:
                self._send_command(["loadfile", filepath, "replace"])
        else:
            subprocess.Popen(
                self._build_cmd(filepath),
                preexec_fn=_new_process_group
            )

    def play_url(self, url: str) -> None:
        """Stream or reload a URL."""
        if self.enable_ipc:
            if not self.is_playing():
                self._start_process(url)
            else:
                self._send_command(["loadfile", url, "replace"])
        else:
            subprocess.Popen(
                self._build_cmd(url),
                preexec_fn=_new_process_group
            )

    def stop(self) -> None:
        """Terminate MPV and clean up socket."""
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception:
                self.process.terminate()
            self.process.wait()
            self.process = None
        if self.enable_ipc:
            self._cleanup_socket()

    def toggle_pause(self) -> None:
        """Toggle play/pause via IPC."""
        self._send_command(["cycle", "pause"])
