import os
import configparser
from pathlib import Path
import platform
import subprocess

def open_path(path: Path) -> None:
    """
    Open a directory or file with the system default application.
    On Linux: uses xdg-open
    On macOS: uses open
    On Windows: uses os.startfile
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{p!r} does not exist")

    match platform.system():
        case "Linux":
            subprocess.run(["xdg-open", str(p)], check=False)
        case "Darwin":
            subprocess.run(["open", str(p)])
        case "Windows":
            # os.startfile only exists on Windows
            os.startfile(str(p))
        case _:
            raise OSError("OS not recognized. Cannot open path.")

class Settings():
    if 'APPDATA' in os.environ:
        _CONFIG_DIR = os.environ['APPDATA']
    elif 'XDG_CONFIG_HOME' in os.environ:
        _CONFIG_DIR = os.environ['XDG_CONFIG_HOME']
    else:
        _CONFIG_DIR = Path.home() / '.config'
    
    _CONFIG_DIR /= 'musicli'
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    _FILE = _CONFIG_DIR / 'settings.ini'

    _DEFAULTS = {
        'app': {
            'settings_directory': 'True',
            'clear_screen': 'True',
            'debug': 'False',
        },
        'player': {
            'player_cmd': 'mpv',
            'ipc_path': str(_CONFIG_DIR / 'ipc-socket')
        },
        'library': {
            'root_path': str(Path.home() / 'Music'),
            'music_formats': 'mp3,wav,opus,flac,m4a',
            'hidden_files': 'False',
            'sort_playlists_by': 'name',
            'sort_tracks_by': 'name',
        },
        'download': {
            'preferred_codec': 'flac',
            'preferred_quality': 'best',
            'embed_thumbnail': 'True',
        }
    }

    config = configparser.ConfigParser()

    @classmethod
    def get_settings_path(cls):
        return cls._FILE

    @classmethod
    def _save(cls):
        """
        Write the settings to disk.
        """
        with cls._FILE.open('w') as file:
            cls.config.write(file)
    
    @classmethod
    def _write_defaults(cls):
        """
        Write the full set of default settings to disk.
        """
        for section, opts in cls._DEFAULTS.items():
            cls.config[section] = opts.copy()
        cls._save()

    @classmethod
    def initialize(cls):
        """
        Load existing settings or write all defaults if missing/empty.
        """
        if cls._FILE.exists():
            cls.config.read(cls._FILE)
            if not cls.config.sections():
                cls._write_defaults()
        else:
            cls._write_defaults()
    
    @classmethod
    def get(cls, section:str, option:str) -> str:
        """
        Return the setting value, loading default for this option if missing.
        """
        # ensure overall initialization was done
        if not cls.config.sections():
            cls.initialize()
        
        # if missing, set default and persist
        if not cls.config.has_section(section) or not cls.config.has_option(section, option):
            if not cls.config.has_section(section):
                cls.config[section] = {}
            cls.config[section][option] = cls._DEFAULTS[section][option]
            cls._save()
            return cls._DEFAULTS[section][option]

        return cls.config.get(section, option)
    
    @classmethod
    def set(cls, section: str, option: str, value: str) -> None:
        """
        Set a setting value and persist to disk.
        """
        if not cls.config.has_section(section):
            cls.config[section] = {}
        cls.config[section][option] = value
        cls._save()

    @classmethod
    def run(cls):
        try:
            path = Settings.get_settings_path().parent if Settings.get('app', 'settings_directory') == "True" else Settings.get_settings_path()
            open_path(path)
        except KeyboardInterrupt:
            pass
