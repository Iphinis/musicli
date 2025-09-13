"""utils.py"""
import os
from pathlib import Path

from settings import Settings


def clear_screen():
    if Settings.get_bool('app', 'clear_screen'):
        command = 'cls' if os.name == 'nt' else 'clear'
        os.system(command)


def ensure_dir(path:str) -> None:
    os.makedirs(path, exist_ok=True)
