from mcp.server.fastmcp import FastMCP

from playlist_library import (
    get_library as library_contents,
    get_player_status,
    next_song,
    pause_music,
    play_playlist,
    play_song_by_title,
    previous_song,
    resume_music,
    set_repeat,
    stop_music,
)

mcp = FastMCP("jukebox-mcp")


@mcp.tool()
def get_library():
    """List all songs by scanning the library folder."""
    return library_contents()


@mcp.tool()
def control_player(action: str, title: str = "", shuffle: bool = False):
    """Control playback.

    action: one of "play", "pause", "resume", "stop", "next",
        "previous", "repeat_on", "repeat_off".
    title: when playing, start at this specific song instead of the
        beginning of the library.
    shuffle: when playing, shuffle the playlist first.
    """
    if action == "play":
        if title:
            return play_song_by_title(title)
        return play_playlist(shuffle)

    if action == "pause":
        return pause_music()

    if action == "resume":
        return resume_music()

    if action == "stop":
        return stop_music()

    if action == "next":
        return next_song()

    if action == "previous":
        return previous_song()

    if action == "repeat_on":
        return set_repeat(True)

    if action == "repeat_off":
        return set_repeat(False)

    return (
        "Unknown action. Use play, pause, resume, stop, next, "
        "previous, repeat_on, or repeat_off."
    )


@mcp.tool()
def get_status():
    """Return the current player status."""
    return get_player_status()


if __name__ == "__main__":
    mcp.run()
