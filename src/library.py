"""library.py"""
from settings import Settings
import os
from fzf import fzf_select
from search import Search
from player import Player
from queue_manager import QueueManager

import utils

class Library:
    def __init__(self, player:Player):
        utils.ensure_dir(Settings.get('library', 'root_path'))

        self.player = player

        self.queue = QueueManager(self.player)

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

    def select_playlist(self, prompt:str="Select a playlist: ", custom_actions:bool=True, start_at_first_element:bool=True) -> str|None:
        """
        Let user select/add/remove a playlist, or go back.
        Returns chosen playlist name or None if back.
        """
        options = self.get_playlists()

        if not self.current_playlist and start_at_first_element and len(options) >= 1:
            start_option = len(self.actions) + (len(self.playlist_actions) if custom_actions else 0)
        elif self.current_playlist:
            start_option = self.current_playlist
        else:
            start_option = 0

        if custom_actions:
            options = self.playlist_actions + options
        options = self.actions + options

        sel = fzf_select(
            options,
            multi=False,
            prompt=prompt,
            start_option=start_option
        ) or []
        choice = sel[0] if sel else None

        # no choice (e.g SIGTERM signal) or back option
        if not choice or choice == self._back_text:
            self.current_option = choice
            return None
        # add playlist option
        elif choice == self._playlist_add_text:
            self.current_option = choice
            playlist = self.create_playlist()
            if playlist:
                self.current_playlist = playlist
                choice = playlist
            return ''
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
            return ''
        else:
            self.current_playlist = choice

        return choice

    def create_playlist(self) -> None:
        """Create a new playlist folder"""
        try:
            name = input("Enter new playlist name: ").strip()
            if name:
                path = self.get_playlist_path(name)
                utils.ensure_dir(path)
                return name
        except KeyboardInterrupt:
            pass
        finally:
            return ''

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

    def select_track(self, playlist:str, prompt:str="Select a track: ", custom_actions:bool=True, start_at_first_element:bool=True) -> str|None:
        """
        Let user select a track in a playlist, or go back.
        Returns track filename or None if back.
        """
        options = self.get_tracks(playlist)

        if not self.current_track and start_at_first_element and len(options) >= 1:
            start_option = len(self.actions) + (len(self.track_actions) if custom_actions else 0)
        elif self.current_track:
            start_option = self.current_track
        else:
            start_option = 0

        if custom_actions:
            options = self.track_actions + options
        options = self.actions + options
        
        sel = fzf_select(
            options,
            multi=False,
            prompt=f"{playlist} - {prompt}",
            start_option=start_option
        ) or []
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

    def add_track(self) -> None:
        Search(library=self, player=self.player, playlist=self.current_playlist).run()

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

    def playlist_action(self):
        """Library button action"""
        playlist = self.select_playlist()

        # no choice or back option
        if playlist is None:
            return None

        if playlist == '' or playlist not in self.get_playlists():
            return self.playlist_action()
        
        return playlist

    def run(self):
        """Display library"""
        while True:
            # enter into the playlist
            playlist = self.playlist_action()

            if not playlist:
                break

            if playlist == '':
                continue

            # choose a track
            while True:
                track = self.select_track(playlist)

                if not track:
                    break

                path = self.get_track_path(playlist, track)

                # manage queue
                tracks = self.get_tracks(playlist)
                try:
                    idx = tracks.index(track)
                except ValueError:
                    print("Selected track not in playlist anymore.")
                    continue

                ordered = tracks[idx:] + tracks[:idx]
                paths = [os.path.abspath(self.get_track_path(playlist, t)) for t in ordered]

                # load the queue into mpv
                self.queue.load_queue(paths)

                self.current_playlist = playlist
                self.current_track = track
