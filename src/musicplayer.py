from utils import clear_screen
from library import Library
from player import Player
from search import Search
from fzf import fzf_select
import signal

class MusicPlayer:
    def __init__(self):
        self.actions = ["Play", "Search", "Quit"]
        self.library = Library()
        self.player = Player()
        self.search = Search(self.library, self.player)

    def enter_playlist(self):
        playlist = self.library.select_playlist()

        if not playlist:
            return None

        if playlist not in self.library.get_playlists():
            return self.enter_playlist()
        
        return playlist

    def play(self):
        while True:
            # enter into the playlist
            playlist = self.enter_playlist()

            if not playlist:
                break

            # choose a track
            while True:
                track = self.library.select_track(playlist)
                if not track:
                    break
                path = self.library.get_track_path(playlist, track)
                self.player.play_track(path)
    
    def stop(self):
        self.player.stop()
        clear_screen()

    def run(self):
        try:
            while True:
                choice_list = fzf_select(self.actions, multi=False, prompt="Action: ")

                if not choice_list:
                    continue

                choice = choice_list[0]

                if choice == "Play":
                    self.play()
                elif choice == "Search":
                    self.search.run()
                else:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
