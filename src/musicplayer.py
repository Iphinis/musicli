from utils import *
from library import Library
from player import Player
from search import Search
from settings import Settings

from fzf import fzf_select
import signal

class MusicPlayer:
    def __init__(self):
        Settings.initialize()

        self.actions = ["Library", "Search", "Settings", "Quit"]

        self.library = Library()
        self.player = Player()
        self.search = Search(self.library, self.player)

    def enter_playlist(self):
        playlist = self.library.select_playlist()

        if not playlist:
            return None

        if playlist != '' and playlist not in self.library.get_playlists():
            return self.enter_playlist()
        
        return playlist

    def library_option(self):
        while True:
            # enter into the playlist
            playlist = self.enter_playlist()

            if not playlist:
                break

            if playlist == '':
                continue

            # choose a track
            while True:
                track = self.library.select_track(playlist)
                if not track:
                    break
                path = self.library.get_track_path(playlist, track)
                self.player.play_track(path)

    def search_option(self):
        self.search.run()
    
    def settings_option(self):
        path = Settings.get_settings_path().parent if Settings.get('app', 'settings_directory') == "True" else Settings.get_settings_path()
        open_path(path)
    
    def stop(self):
        self.player.stop()
        clear_screen()

    def run(self):
        try:
            while True:
                choice_list = fzf_select(self.actions, multi=False, prompt="Musicli: ")

                if not choice_list:
                    continue

                choice = choice_list[0]

                if choice == "Library":
                    self.library_option()
                elif choice == "Search":
                    self.search_option()
                elif choice == "Settings":
                    self.settings_option()
                else:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
