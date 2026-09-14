from enum import StrEnum

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
    shutdown_player,
    start_playlist_watcher,
    stop_music,
)

mcp = FastMCP("jukebox-mcp")


class PlayerAction(StrEnum):
    PLAY = "play"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"
    REPEAT_ON = "repeat_on"
    REPEAT_OFF = "repeat_off"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            return next((action for action in cls if action.value == normalized), None)
        return None


@mcp.tool()
def get_library():
    """List all songs by scanning the library folder."""
    return library_contents()


@mcp.tool()
def control_player(action: PlayerAction, title: str = "", shuffle: bool = False):
    """Control playback.

    action: one of "play", "pause", "resume", "stop", "next",
        "previous", "repeat_on", "repeat_off".
    title: when playing, start at this specific song instead of the
        beginning of the library.
    shuffle: when playing, shuffle the playlist first.
    """
    if not isinstance(action, str):
        raise TypeError("Action must be text.")

    if not isinstance(title, str):
        raise TypeError("Title must be text.")

    try:
        action = PlayerAction(action)
    except ValueError as exc:
        raise ValueError(
            "Unknown action. Use play, pause, resume, stop, next, previous, "
            "repeat_on, or repeat_off."
        ) from exc
    title = title.strip()

    if action is PlayerAction.PLAY:
        if title:
            return play_song_by_title(title)
        return play_playlist(shuffle)

    if action is PlayerAction.PAUSE:
        return pause_music()

    if action is PlayerAction.RESUME:
        return resume_music()

    if action is PlayerAction.STOP:
        return stop_music()

    if action is PlayerAction.NEXT:
        return next_song()

    if action is PlayerAction.PREVIOUS:
        return previous_song()

    if action is PlayerAction.REPEAT_ON:
        return set_repeat(True)

    if action is PlayerAction.REPEAT_OFF:
        return set_repeat(False)

    raise AssertionError(f"Unhandled player action: {action}")


@mcp.tool()
def get_status():
    """Return the current player status."""
    return get_player_status()


def main():
    try:
        start_playlist_watcher()
        mcp.run()
    finally:
        shutdown_player()


if __name__ == "__main__":
    main()
