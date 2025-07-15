#!/usr/bin/env python3

from library import Library
from player import Player
import os
from fzf import fzf_select

class MusicPlayer():
    def __init__(self):
        self.library = Library()
        self.player = Player()
        self.actions = ["Play a track", "Quit"]

    def choose_music(self):
        self.library.update()

        playlist = self.library.select_playlist()
        track = self.library.select_track(playlist)

        path = os.path.join(self.library.root_path, playlist, track)

        print(f"Playing {track}...")
        self.player.play_track(path)
    
    def run(self):
        while True:
            choice = fzf_select(self.actions)
            if choice == self.actions[0]:
                    self.choose_music()
            else:
                self.player.stop_process()
                break

if __name__ == "__main__":
    MusicPlayer().run()

