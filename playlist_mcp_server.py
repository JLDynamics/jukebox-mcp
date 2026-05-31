from mcp.server.fastmcp import FastMCP

from playlist_library import (
    get_player_status,
    import_song_from_inbox,
    list_inbox_mp3_files,
    list_moods,
    list_songs,
    next_song,
    pause_music,
    play_mood_playlist,
    resume_music,
    shuffle_mood_playlist,
    stop_music,
)

mcp = FastMCP("music-playlist-maker")


@mcp.tool()
def list_inbox_songs():
    return list_inbox_mp3_files()


@mcp.tool()
def import_inbox_song(file_name: str, mood: str):
    return import_song_from_inbox(file_name, mood)


@mcp.tool()
def shuffle_playlist_by_mood(mood: str):
    return shuffle_mood_playlist(mood)


@mcp.tool()
def pause_player():
    return pause_music()


@mcp.tool()
def play_next_song():
    return next_song()


@mcp.tool()
def get_status():
    return get_player_status()


@mcp.tool()
def play_playlist_by_mood(mood: str):
    return play_mood_playlist(mood)


@mcp.tool()
def stop_player():
    return stop_music()


@mcp.tool()
def resume_player():
    return resume_music()


@mcp.tool()
def get_moods():
    return list_moods()


@mcp.tool()
def get_songs_by_mood(mood: str):
    songs = list_songs(mood)

    if songs is None:
        return "That mood does not exist."

    return songs


if __name__ == "__main__":
    mcp.run()
