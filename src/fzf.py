"""fzf.py"""
import subprocess
import os

from settings import Settings

def fzf_select(options:list[str], multi:bool=False, prompt:str="", start_option:str|None=None, raise_except:bool=False) -> list[str]:
    """
    Display options in fzf and return selected option(s).

    Args:
        options: List of strings to show in fzf.
        multi: If True, allow multi-selection.
        prompt: Prompt text to display.
        start_option: If provided, initial highlighted option.
    """
    
    fzf_cmd = [
        "fzf",
        "--prompt", prompt,
        "--ansi",
        "--reverse",
        "--cycle",
        "--no-bold",
        "--expect", "ctrl-d,ctrl-z"
    ]
    if multi:
        fzf_cmd.append("--multi")
    if start_option:
        try:
            idx = options.index(start_option)
            cursor_pos = idx + 1  # fzf is 1-based
        except ValueError:
            # fallback if option not found
            cursor_pos = 1
        fzf_cmd += ["--bind", f"load:pos({cursor_pos})"]

    fzf = subprocess.run(
        fzf_cmd,
        input="\n".join(options),
        text=True,
        capture_output=True,
    )

    if raise_except and fzf.returncode != 0:
        raise KeyboardInterrupt
    
    if not fzf.stdout:
        return []
    
    return fzf.stdout.strip().split("\n")
