"""queue_manager.py"""
import os
from typing import List, Optional
from player import Player

import threading, time

class QueueManager:
    """
    Application-side queue that mirrors into mpv via IPC safely.
    Uses Player.wait_for_playlist_count and events to avoid races.
    """

    def __init__(self, player:Player):
        self.player = player
        self.queue:List[str] = [] # keep absolute paths or URLs
        self._lock = threading.Lock()

        self._loading = False

        self.player.start_event_loop(self._on_mpv_event) # start event loop in player and forward events to our handler
        self._current_pos:Optional[int] = None # cached mpv playlist-pos (updated on start-file)

    def _abs(self, path:str) -> str:
        return os.path.abspath(path) if not (path.startswith("http://") or path.startswith("https://")) else path

    # -------------------------
    # core operations (safe)
    # -------------------------
    def load_queue(self, paths:List[str]) -> None:
        """
        Replace current queue and start playing at paths[0].
        """
        if not paths:
            return

        abs_paths = [self._abs(p) for p in paths]

        self._loading = True

        try:
            # ensure mpv running
            self.player.start_idle()

            # replace with the first item
            self.player.ipc_send(["loadfile", abs_paths[0], "replace"])

            # wait until mpv reports playlist-count >= 1
            if not self.player.wait_for_playlist_count(1):
                print("[queue] warning: mpv did not report 1 playlist item in time")

            # append remaining items, waiting for playlist-count increments
            base_count = int(self.player.get_property("playlist-count") or 0)

            for p in abs_paths[1:]:
                # send append and wait for playlist-count to increase by 1
                self.player.ipc_send(["loadfile", p, "append"])
                
                wanted = base_count + 1

                if self.player.wait_for_playlist_count(wanted):
                    base_count = wanted
                else:
                    # fallback: short sleep and attempt to continue; also sync from mpv
                    print(f"[queue] warning: append not observed in time for {p}")
                    time.sleep(0.1)
            
            # reconciliation with mpv
            self.sync_from_mpv(abs_paths.copy())

        finally:
            # clear loading guard in all cases so event thread resumes normal sync
            self._loading = False

    def append(self, path:str, play_now:bool=False) -> None:
        """Append path to the end of the queue in a safe manner."""
        p = self._abs(path)
        with self._lock:
            self.queue.append(p)
        mode = "append-play" if play_now else "append"
        self.player.ipc_send(["loadfile", p, mode])
        # if not play_now, we can optionally wait for playlist-count change
        if not play_now:
            try:
                cur = int(self.player.get_property("playlist-count") or 0)
            except Exception:
                cur = 0
            self.player.wait_for_playlist_count(cur + 1, timeout=2.0)

    def insert_at(self, index:int, path:str, play_now:bool = False) -> None:
        p = self._abs(path)
        with self._lock:
            if index < 0:
                index = 0
            if index >= len(self.queue):
                # append fallback
                self.queue.append(p)
                mode = "append-play" if play_now else "append"
                self.player.ipc_send(["loadfile", p, mode])
                return
            self.queue.insert(index, p)
        mode = "insert-at-play" if play_now else "insert-at"
        # send insert-at (mpv >= 0.38) - if not supported, mpv will error; could fallback to append+move
        self.player.ipc_send(["loadfile", p, mode, str(index)])
        # best-effort wait (playlist-count should rise)
        try:
            cur = int(self.player.get_property("playlist-count") or 0)
        except Exception:
            cur = 0
        self.player.wait_for_playlist_count(cur + 1, timeout=2.0)

    def remove_at(self, index: int) -> None:
        """Remove by index from our queue and mpv playlist. Uses numeric remove (careful)."""
        with self._lock:
            if index < 0 or index >= len(self.queue):
                return
            # pop locally
            self.queue.pop(index)
        # ask mpv to remove that index
        self.player.ipc_send(["playlist-remove", index])
        # mpv will update playlist-count and start-file; event thread will sync props

    def remove_path(self, path: str) -> None:
        """Remove the first matching path from queue (by absolute path)."""
        p = self._abs(path)
        with self._lock:
            try:
                idx = self.queue.index(p)
            except ValueError:
                # sync from mpv (best-effort)
                self.sync_from_mpv()
                try:
                    idx = self.queue.index(p)
                except ValueError:
                    return
        self.remove_at(idx)

    def move(self, old_index: int, new_index: int) -> None:
        with self._lock:
            if old_index < 0 or old_index >= len(self.queue):
                return
            item = self.queue.pop(old_index)
            self.queue.insert(new_index, item)
        self.player.ipc_send(["playlist-move", old_index, new_index])

    def play_index(self, index: int) -> None:
        """Jump mpv playback to playlist index."""
        self.player.ipc_send(["set_property", "playlist-pos", index])

    def current_index(self) -> Optional[int]:
        val = self.player.get_property("playlist-pos")
        try:
            return int(val) if val is not None else None
        except Exception:
            return None

    # -------------------------
    # sync helpers & events
    # -------------------------
    def sync_from_mpv(self, fallback:List[str]=[]) -> None:
        """
        Query mpv's playlist items and rebuild our internal queue to match the mpv order.
        This uses get_property for playlist-count and playlist/<i>/filename.
        """

        try:
            count = int(self.player.get_property("playlist-count") or 0)
        except Exception:
            count = 0

        new_q = []

        for i in range(count):
            fname = self.player.get_property(f"playlist/{i}/filename")
            if not fname:
                fname = self.player.get_property(f"playlist/{i}/path") or self.player.get_property(f"playlist/{i}/title")
            if fname:
                new_q.append(fname)

        with self._lock:
            if new_q:
                self.queue = new_q
            else:
                self.queue = fallback

    def _on_mpv_event(self, obj:dict):
        """
        MPV event callback from Player. We care about 'start-file' to keep in-sync.
        """
        ev = obj.get("event")
        if ev == "start-file":
            pos = obj.get("playlist-pos")
            try:
                pos = int(pos) if pos is not None else None
            except Exception:
                pos = None
            self._current_pos = pos
            # rebuild our queue from mpv (safe point)
            self.sync_from_mpv()
