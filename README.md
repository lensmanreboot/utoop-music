[![Latest Release](https://img.shields.io/github/v/release/mirajlensman/utoop-music?label=Latest%20Release)](https://github.com/mirajlensman/utoop-music/releases/latest)

# uToop Music

uToop Music is a lightweight, GTK 3-based music player designed for Maemo Leste on the Nokia N900. It provides a terminal-styled interface for searching, streaming, and downloading YouTube audio.

## Features
- **Robust Search**: Uses `yt-dlp` directly for fast and reliable YouTube searches.
- **Local & Online Modes**: Easily switch between online streaming and local file playback.
- **Persistent State**: Toggling modes preserves your previous search results and filter status.
- **Keyboard Control**: Search-focused input and arrow-key seeking.
- **Download Management**: Built-in downloader with existing-file check (Download Again / Skip).
- **Configurable**: Defaults to `/home/user/MyDocs/uToopDownloads` on N900, falls back to `~/uToopDownloads` on other systems.

## Development & Modification
This project is structured as a standard Debian package.

### Source Code
The Python source is located in `ut_api.py`, `ut_app.py`, and `ut_engine.py`.

### Packaging Structure
- `utoop-music-pkg/DEBIAN/`: Package metadata and control files (edit `control` to add dependencies).
- `utoop-music-pkg/usr/bin/`: Executable wrapper script.
- `utoop-music-pkg/usr/lib/python3/dist-packages/utoop_music/`: Python source files.
- `utoop-music-pkg/usr/share/applications/`: Desktop entries for the application menu.
- `utoop-music-pkg/usr/share/icons/`: Application icon.

### How to Build
To build the `.deb` package from source, follow these steps:

```bash
# 1. Clone the repository
git clone https://github.com/mirajlensman/utoop-music.git
cd utoop-music

# 2. Make the build script executable and run it
chmod +x build.sh
./build.sh

# 3. Install the generated package
sudo dpkg -i utoop-music_*.deb
```

## License
Distributed under the GNU GPLv3 License. See `LICENSE` for more information.

## Contact
Miraj Lensman - mirajlensman@gmail.com
