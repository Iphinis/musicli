#!/usr/bin/env python3
"""main.py"""

from utils import clear_screen
from library import Library
from player import Player
from search import Search
from search_file import SearchFile
from settings import Settings
from fzf import fzf_select

class MusicPlayer:
    """
    Main class of musicli.
    """
    def __init__(self):
        """
        Initialize MusicPlayer.
        """
        Settings.initialize()

        self.actions = ["Library", "Search", "Download", "Settings", "Quit"]

        self.player = Player()
        self.library = Library(self.player)
        self.search = Search(self.library, self.player)
        self.search_file = SearchFile(self.library, self.player)

    def enter_library(self) -> None:
        """
        Enter library menu.
        """
        self.library.run()

    def search_option(self) -> None:
        """
        Enter search menu.
        """
        self.search.run()

    def download_option(self) -> None:
        """
        Enter download menu.
        """
        self.search_file.run()

    def settings_option(self) -> None:
        """
        Enter settings menu.
        """
        Settings.run()

    def run(self) -> None:
        """
        Run musicli.
        """
        try:
            while True:
                choice_list = fzf_select(self.actions, multi=False, \
                    prompt="Musicli", raise_except=True)

                if not choice_list:
                    continue

                choice = choice_list[0]

                if choice == self.actions[0]:
                    self.enter_library()
                elif choice == self.actions[1]:
                    self.search_option()
                elif choice == self.actions[2]:
                    self.download_option()
                elif choice == self.actions[-2]:
                    self.settings_option()
                else:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            # stop the active media player
            self.player.stop()
            clear_screen()

if __name__ == "__main__":
    MusicPlayer().run()
