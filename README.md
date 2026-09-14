# Jukebox MCP

A local music player controlled from Claude Code through MCP.

Drop your audio files into the `library/` folder and control playback through MCP tools. The folder is the source of truth — no database or JSON file to maintain.

## Features

- Auto-scans the `library/` folder for audio files (mp3, ogg, wav, flac, m4a, aac, opus)
- Play or shuffle the library, or play a specific song by title
- Pause, resume, stop, next, and previous
- Repeat mode to loop the playlist
- Player status with current song and position

Playback is handled by VLC (via python-vlc), so any format VLC can play works — including m4a/AAC.

## What This Project Does Not Do

This project does not download music from YouTube or any streaming service. Users provide their own legal audio files.

## Requirements

- Python 3.13+
- uv
- Claude Code
- [VLC media player](https://www.videolan.org/vlc/) installed on your system
- Local audio files

## Setup

Clone the repo:

```powershell
git clone https://github.com/JLDynamics/jukebox-mcp.git
cd jukebox-mcp
```

Install dependencies:

```powershell
uv sync
```

Create the library folder (also created automatically on first run) and put your audio files in it:

```powershell
mkdir library
```

## Claude Code MCP Setup

From the project folder (Windows):

```powershell
claude mcp add jukebox-mcp -- .\.venv\Scripts\python.exe playlist_mcp_server.py
```

macOS/Linux:

```bash
claude mcp add jukebox-mcp -- ./.venv/bin/python playlist_mcp_server.py
```

Restart Claude Code after adding the server.

Then ask Claude Code:

```text
Use the jukebox-mcp server to show my music library.
```

## Workflow

1. Copy audio files into `library/`.
2. Ask Claude Code to show your library.
3. Ask Claude Code to play or shuffle the library, or a specific song.
4. Use the player controls (pause, resume, next, previous, stop, repeat) and status tool.

## MCP Tools

- `get_library` — scan the library folder and list all songs
- `control_player(action, title, shuffle)` — play, pause, resume, stop, next, previous, repeat_on, repeat_off
- `get_status` — current song, position, and repeat state

## Local Files

The following are intentionally ignored by Git:

- `library/`
- audio files such as `.mp3`, `.wav`, `.flac`, `.m4a`, and `.aac`

This keeps personal music files out of the public repository.

## Tests

The automated tests use a fake VLC player, so they do not play audio or require
an audio output device:

```bash
uv run python -m unittest discover -s tests -v
```

## License

MIT
