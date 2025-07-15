import subprocess
import shlex

class Player():
    def __init__(self):
        self.process = None
    
    def is_playing(self) -> bool:
        return self.process and not self.process.poll()
    
    def stop_process(self) -> None:
        """Stop the current process"""
        if self.is_playing():
            self.process.terminate()
            self.process.wait()
        self.process = None

    def play_track(self, track:str):
        """Play a track"""
        if self.is_playing():
            # Stop the previous track
            self.stop_process()

        cmd = f"ffplay -loglevel warning {shlex.quote(track)}"

        self.process = subprocess.Popen(
            shlex.split(cmd),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    
    def pause_track(self):
        """(Un)Pause the current track"""
        if self.is_playing():
            try:
                self.process.stdin.write(b"p")
                self.process.sdin.flush()
            except BrokenPipeError:
                pass
    

