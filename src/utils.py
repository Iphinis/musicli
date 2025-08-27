import os
from pathlib import Path

from settings import Settings

def clear_screen():
    if Settings.get('app', 'clear_screen') == 'True':
        command = 'cls' if os.name == 'nt' else 'clear'
        os.system(command)

def ensure_dir(path:str) -> None:
    os.makedirs(path, exist_ok=True)
