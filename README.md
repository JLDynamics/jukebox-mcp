# Music Playlist Maker MCP Server

A local MP3 music library controlled from Claude Code through MCP.

This project lets you organize your own MP3 files by mood, import songs from a local inbox folder, and control playback through MCP tools.

## Features

- List available moods
- List songs by mood
- Import MP3 files from `inbox/`
- Play mood playlists
- Shuffle playlists
- Pause, resume, stop, and skip songs
- Check current player status
- Delete songs from the local library

## What This Project Does Not Do

This project does not download music from YouTube or any streaming service. Users provide their own legal MP3 files.

## Requirements

- Python 3.13+
- uv
- Claude Code
- Local MP3 files

## Platform

This project is currently tested on Windows.

## Setup

Clone the repo:

```powershell
git clone https://github.com/JLDynamics/music-playlist-maker.git
cd music-playlist-maker
```

Install dependencies:

```powershell
uv sync
```

Create your personal songs file:

```powershell
copy songs.example.json songs.json
```

Create local music folders:

```powershell
mkdir inbox
mkdir library
mkdir library\happy
mkdir library\sad
mkdir library\focused
mkdir library\angry
```

## Claude Code MCP Setup

From the project folder:

```powershell
claude mcp add music-playlist-maker -- .\.venv\Scripts\python.exe playlist_mcp_server.py
```

Restart Claude Code after adding the server.

Then ask Claude Code:

```text
Use the music-playlist-maker MCP server to list my moods.
```

## Workflow

1. Put MP3 files into `inbox/`.
2. Ask Claude Code to list inbox songs.
3. Ask Claude Code to import a song into a mood.
4. Ask Claude Code to play or shuffle a mood playlist.
5. Use pause, resume, next, stop, and status tools to control playback.

## MCP Tools

- `get_moods`
- `get_songs_by_mood`
- `list_inbox_songs`
- `import_inbox_song`
- `delete_song_by_title`
- `play_playlist_by_mood`
- `shuffle_playlist_by_mood`
- `pause_player`
- `resume_player`
- `stop_player`
- `play_next_song`
- `get_status`

## Local Files

The following are intentionally ignored by Git:

- `songs.json`
- `inbox/`
- `library/`
- audio files such as `.mp3`, `.wav`, `.flac`, `.m4a`, and `.aac`

This keeps personal music files and playlist data out of the public repository.

## License

MIT
