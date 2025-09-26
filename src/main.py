#!/usr/bin/env python3
"""main.py"""

import utils
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
        self.current_action = None

        self.player = Player()
        self.library = Library(self.player)
        self.search = Search(self.library, self.player)
        self.search_file = SearchFile(self.library, self.player)

    def enter_library(self) -> None:
        """Enter library menu."""
        self.library.run()

    def search_option(self) -> None:
        """Enter search menu."""
        self.search.run()

    def download_option(self) -> None:
        """Enter download menu."""
        self.search_file.run()

    def settings_option(self) -> None:
        """Enter settings menu."""
        Settings.run()

    def run(self) -> None:
        """Run musicli."""
        try:
            while True:
                choice = fzf_select(
                    self.actions,
                    multi=False,
                    prompt="Musicli ",
                    start_option=self.current_action,
                    raise_except=True
                    )[0]

                if not choice:
                    continue

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

                self.current_action = choice
                
        except KeyboardInterrupt:
            pass
        finally:
            # stop the active media player
            self.player.stop()
            utils.clear_screen()

if __name__ == "__main__":
    MusicPlayer().run()
