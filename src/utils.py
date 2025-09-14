"""utils.py"""
import os, platform
from pathlib import Path

from settings import Settings


def clear_screen():
    if Settings.get_bool('app', 'clear_screen'):
        command = 'cls' if os.name == 'nt' else 'clear'
        os.system(command)


def ensure_dir(path:str) -> None:
    os.makedirs(path, exist_ok=True)


def input_with_placeholder(input_text:str="Input: ", placeholder:str="") -> str:
        """Prefill input with last query as placeholder, if compatible with OS"""
        match platform.system():
            case "Linux":
                import readline
                def hook():
                    readline.insert_text(placeholder)
                    readline.redisplay()
                readline.set_pre_input_hook(hook)
        try:
            print()
            inp = input(input_text).strip()
            return inp
        finally:
            match platform.system():
                case "Linux":
                    readline.set_pre_input_hook()
