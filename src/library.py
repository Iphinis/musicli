import os
from fzf import fzf_select
from search import Search

from utils import *

class Library:
    def __init__(self, root_path:str="/home/iphinis/Music/", music_formats: list[str] = None):
        self.root_path = root_path
        self.music_formats = music_formats or ["mp3", "wav", "opus", "flac", "m4a"]

        self.last_playlist:str = None
        self.last_track:str = None
        
        ensure_dir(self.root_path)

        self.actions = ["[ Back ]"]
        self.playlist_actions = ["[ New Playlist ]", "[ Remove Playlist ]"]
        self.track_actions = ["[ Add Track ]", "[ Delete Track ]"]

    def get_playlists(self) -> list[str]:
        """Return list of subdirectories in root_path, excluding hidden"""
        try:
            return sorted(
                [d for d in os.listdir(self.root_path)
                 if os.path.isdir(os.path.join(self.root_path, d)) and not d.startswith('.')]
            )
        except FileNotFoundError:
            return []

    def get_playlist_path(self, playlist:str) -> str:
        """Return full path for a playlist"""
        return os.path.join(self.root_path, playlist)

    def get_track_path(self, playlist:str, track:str) -> str:
        """Return full path for a track"""
        return os.path.join(self.get_playlist_path(playlist), track)

    def get_files(self, playlist:str) -> list[str]:
        """Return all file names in a playlist directory"""
        p = self.get_playlist_path(playlist)
        try:
            return os.listdir(p)
        except FileNotFoundError:
            return []

    def is_track(self, name: str) -> bool:
        """Return True if file is audio track based on extension"""
        return any(name.lower().endswith(f".{ext}") for ext in self.music_formats)

    def get_tracks(self, playlist: str) -> list[str]:
        """Return sorted list of tracks in playlist"""
        return sorted([f for f in self.get_files(playlist) if self.is_track(f)])

    def create_playlist(self) -> None:
        """Create a new playlist folder"""
        name = input("Enter new playlist name: ").strip()
        if name:
            self.create_playlist(name)
            path = self.get_playlist_path(name)
            ensure_dir(path)
    
    def remove_playlist(self, prompt="Select a playlist to REMOVE: ") -> None:
        """Remove a playlist folder"""
        playlist = self.select_playlist(prompt=prompt, custom_actions=False)
        if playlist:
            path = self.get_playlist_path(playlist)
            try:
                os.rmdir(path)
            except OSError as e:
                self.remove_playlist(str(e))
        return None

    def select_playlist(self, prompt="Select a playlist: ", custom_actions=True) -> str | None:
        """
        Let user select a playlist, create new, or go back.
        Returns chosen playlist name or None if back.
        """
        
        options = self.get_playlists() + self.actions
        if custom_actions:
            options = self.playlist_actions + options

        sel = fzf_select(options, multi=False, prompt=prompt, start_option=self.last_playlist) or []
        choice = sel[0] if sel else None

        # no choice (e.g SIGTERM signal) or back option
        if not choice or choice == self.actions[0]:
            return None
        # add playlist option
        elif choice == self.playlist_actions[0]:
            playlist = self.create_playlist()
            self.last_playlist = playlist
            choice = playlist
        # remove playlist option
        elif choice == self.playlist_actions[1]:
            if not self.remove_playlist():
                choice = None
        
        self.last_playlist = choice
        return choice
    
    def add_track(self) -> None:
        Search(self).run()
    
    def delete_track(self, prompt="Select a playlist to REMOVE: ") -> None:
        """Delete a track"""
        track = self.select_track(prompt=prompt, custom_actions=False)
        if track:
            path = self.get_track_path(self.last_playlist, track)
            try:
                os.rmdir(path)
            except OSError as e:
                self.delete_track(str(e))
        return None

    def select_track(self, playlist: str, prompt="Select track: ", custom_actions=True) -> str | None:
        """
        Let user select a track in a playlist, or go back.
        Returns track filename or None if back.
        """
        tracks = self.get_tracks(playlist)

        options = tracks + self.actions
        if custom_actions:
            options = self.track_actions + options
        
        sel = fzf_select(options, multi=False, prompt=prompt, start_option=self.last_track) or []
        choice = sel[0] if sel else None

        # add track
        if choice == self.track_actions[0]:
            self.add_track()
        # remove track
        elif choice == self.track_actions[1]:
            self.delete_track()
        # No choice or back
        elif not choice or choice == self.actions[0]:
            self.last_track = None
            return None
        
        self.last_track = choice
        return choice
