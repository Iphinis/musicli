import os
from fzf import fzf_select

class Library():
    def __init__(self, root_path:str="/home/iphinis/Music/", music_formats:list[str]=["mp3", "wav", "opus", "flac", "wav"]):
        self.root_path = root_path
        self.music_formats = music_formats

        self.library = {}

    def get_playlists(self, path:str) -> list[str]:
        path, playlists, files = next(os.walk(self.root_path))
        return playlists

    def get_files(self, playlist:str) -> list[str]:
        path, playlists, files = next(os.walk(os.path.join(self.root_path, playlist)))
        return files

    def is_track(self, name:str) -> bool:
        for format in self.music_formats:
            if name.endswith(format):
                return True
        return False

    def get_tracks(self, playlist:str) -> list[str]:
        return list(filter(self.is_track, self.get_files(playlist)))

    def update(self) -> None:
        """Update the library"""
        playlists = self.get_playlists(self.root_path)

        if playlists:
            for p in playlists:
                tracks = self.get_tracks(p)
                self.library[p] = tracks

    def select_playlist(self) -> str:
        """Display the library"""
        choice = fzf_select(self.library.keys())
        return choice
    
    def select_track(self, playlist:str) -> str:
        choice = fzf_select(self.library[playlist])
        return choice
