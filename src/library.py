from settings import Settings
import os
from fzf import fzf_select
from search import Search

from utils import *

class Library:
    def __init__(self):
        ensure_dir(Settings.get('library', 'root_path'))

        self.music_formats = Settings.get('library', 'music_formats').split(',')

        self.current_playlist : str = None
        self.current_track : str = None
        
        self.current_option : str = None

        self._back_text = "[ Back ]"
        self._playlist_add_text = "[ New Playlist ]"
        self._playlist_remove_text = "[ Remove Playlist ]"
        self._track_add_text = "[ Add Track ]"
        self._track_delete_text = "[ Delete Track ]"

        self.actions = [self._back_text]
        self.playlist_actions = [self._playlist_add_text, self._playlist_remove_text]
        self.track_actions = [self._track_add_text, self._track_delete_text]

    def get_playlists(self) -> list[str]:
        """Return list of subdirectories in root_path, excluding hidden"""
        playlists = []
        try:
            playlists = [d for d in os.listdir(Settings.get('library', 'root_path')) \
                 if os.path.isdir(os.path.join(Settings.get('library', 'root_path'), d)) and (not d.startswith('.') if Settings.get('library', 'hidden_files') == 'False' else True)]
        except FileNotFoundError:
            return playlists
        
        match Settings.get('library', 'sort_playlists_by'):
            case 'name':
                return sorted(playlists)
            case _:
                return playlists

    def get_playlist_path(self, playlist:str) -> str:
        """Return full path for a playlist"""
        return os.path.join(Settings.get('library', 'root_path'), playlist)

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
        tracks = [f for f in self.get_files(playlist) if self.is_track(f)]
        
        match Settings.get('library', 'sort_tracks_by'):
            case 'name':
                return sorted(tracks)
            case _:
                return tracks

    def create_playlist(self) -> None:
        """Create a new playlist folder"""
        name = input("Enter new playlist name: ").strip()
        if name:
            path = self.get_playlist_path(name)
            ensure_dir(path)
        return name
    
    def remove_playlist(self, prompt="Select a playlist to DELETE: ") -> None:
        """
        Remove a playlist folder and returns its name
        Returns '' if it did not succeed.
        """
        playlist = self.select_playlist(prompt=prompt, custom_actions=False)
        if playlist:
            path = self.get_playlist_path(playlist)
            try:
                os.rmdir(path)
                return playlist
            except OSError as e:
                return self.remove_playlist(str(e))
        return ''

    def select_playlist(self, prompt="Select a playlist: ", custom_actions=True) -> str | None:
        """
        Let user select a playlist, create new, or go back.
        Returns chosen playlist name or None if back.
        """
        options = self.get_playlists() + self.actions
        if custom_actions:
            options = self.playlist_actions + options

        sel = fzf_select(options, multi=False, prompt=prompt, start_option=self.current_playlist) or []
        choice = sel[0] if sel else None

        # no choice (e.g SIGTERM signal) or back option
        if not choice or choice == self._back_text:
            self.current_option = choice
            return None
        # add playlist option
        elif choice == self._playlist_add_text:
            self.current_option = choice
            playlist = self.create_playlist()
            self.current_playlist = playlist
            choice = playlist
        # remove playlist option
        elif choice == self._playlist_remove_text:
            self.current_option = choice
            playlist = self.remove_playlist()
            self.current_playlist = playlist

            # if it is deleted
            if playlist:
                choice = ''
                self.current_playlist = ''
            else:
                choice = playlist
                self.current_playlist = playlist

        return choice
    
    def add_track(self) -> None:
        Search(self, playlist=self.current_playlist).run()
    
    def delete_track(self, prompt=f"Select a track to DELETE: ") -> None:
        """Delete a track"""
        track = self.select_track(self.current_playlist, prompt=prompt, custom_actions=False)
        if track:
            path = self.get_track_path(self.current_playlist, track)
            try:
                os.remove(path)
            except OSError as e:
                return self.delete_track(str(e))
        return ''

    def select_track(self, playlist:str, prompt="Select a track: ", custom_actions=True) -> str|None:
        """
        Let user select a track in a playlist, or go back.
        Returns track filename or None if back.
        """
        tracks = self.get_tracks(playlist)

        options = tracks + self.actions
        if custom_actions:
            options = self.track_actions + options
        
        sel = fzf_select(options, multi=False, prompt=f"{playlist} - {prompt}", start_option=self.current_track) or []
        choice = sel[0] if sel else None

        # add track
        if choice == self._track_add_text:
            self.add_track()
        # delete track
        elif choice == self._track_delete_text:
            return self.delete_track()
        # No choice or back
        elif not choice or choice == self._back_text:
            self.current_track = None
            return None

        self.current_track = choice
        return choice
