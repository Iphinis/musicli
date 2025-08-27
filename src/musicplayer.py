from utils import clear_screen
from library import Library
from player import Player
from search import Search
from settings import Settings

from fzf import fzf_select

class MusicPlayer:
    def __init__(self):
        Settings.initialize()

        self.actions = ["Library", "Search", "Settings", "Quit"]

        self.player = Player()
        self.library = Library(self.player)
        self.search = Search(self.library, self.player)

    def enter_library(self):
        self.library.run()

    def search_option(self):
        self.search.run()
    
    def settings_option(self):
        Settings.run()
    
    def stop(self):
        self.player.stop()
        clear_screen()

    def run(self):
        try:
            while True:
                choice_list = fzf_select(self.actions, multi=False, prompt="Musicli: ", raise_except=True)

                if not choice_list:
                    continue

                choice = choice_list[0]

                if choice == "Library":
                    self.enter_library()
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
