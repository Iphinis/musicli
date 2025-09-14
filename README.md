# Dependencies
## Python
- `python3`
- `pipenv`

## Programs
- [fzf](https://github.com/junegunn/fzf/)
- `xdg-user-dirs` and `xdg-utils` (Linux only)
- [ffmpeg](https://ffmpeg.org/)
- [mpv](https://github.com/mpv-player/mpv)

# Installation and usage
After installing the minimal dependencies listed above:

1. Change to the cloned project directory.
2. Install other python dependencies with:
```
pipenv install
```
3. Use the pipenv shell with the installed dependencies:
```
pipenv shell
```
4. Run the program:
```
python src/main.py
```

At this time, there's no release available.

# Settings
You can open the settings configuration file from within the program. The `settings.ini` file location depends on your operating system.

At this time, settings are applied at startup. Rerun the program to apply changes.

# Cross-platform
The program has been developed on Linux only. Compatibility with other kernels or operating systems is not guaranteed.

# Note
> Users bear full responsibility for their actions and any legal consequences. We do not endorse or support the unauthorized downloading of copyrighted content and disclaim any liability for users’ conduct.

Consult the project license and the Terms of Service of the services used by this project for more information.
