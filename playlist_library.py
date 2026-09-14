import logging
import os
import random
import threading


logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIBRARY_DIR = os.path.join(BASE_DIR, "library")
AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav", ".flac", ".m4a", ".aac", ".opus")

try:
    import vlc
except Exception:
    vlc = None

_instance = None
_player = None
player_ready = False

PLAYER_UNAVAILABLE = "Audio player not available. Is VLC media player installed?"

state_lock = threading.RLock()
shutdown_event = threading.Event()
playlist_thread = None

current_playlist = []
current_song_index = 0
playlist_is_active = False
music_is_paused = False
repeat_is_on = False


def initialize_player():
    """Create the VLC objects when the server starts or playback is requested."""
    global _instance
    global _player
    global player_ready

    with state_lock:
        if player_ready:
            return True

        if vlc is None:
            return False

        new_instance = None
        try:
            new_instance = vlc.Instance("--intf=dummy", "--no-video")
            new_player = new_instance.media_player_new() if new_instance else None
        except Exception:
            if new_instance is not None:
                try:
                    new_instance.release()
                except Exception:
                    logger.exception("Could not release incomplete VLC instance")
            logger.exception("Could not initialize VLC")
            return False

        if new_player is None:
            if new_instance is not None:
                try:
                    new_instance.release()
                except Exception:
                    logger.exception("Could not release incomplete VLC instance")
            return False

        _instance = new_instance
        _player = new_player
        player_ready = True
        return True


def scan_library():
    """Scan the library/ folder for audio files.

    The folder on disk is the source of truth. Every audio file
    directly inside library/ is a song.
    """
    try:
        os.makedirs(LIBRARY_DIR, exist_ok=True)
        file_names = sorted(os.listdir(LIBRARY_DIR))
    except OSError as exc:
        raise RuntimeError(f"Could not scan library folder: {exc}") from exc

    songs = []

    for file_name in file_names:
        file_path = os.path.join(LIBRARY_DIR, file_name)
        if os.path.isfile(file_path) and file_name.lower().endswith(AUDIO_EXTENSIONS):
            songs.append(
                {
                    "title": os.path.splitext(file_name)[0],
                    "file": file_path,
                }
            )

    return songs


def get_library():
    return [song["title"] for song in scan_library()]


def get_player_status():
    with state_lock:
        if len(current_playlist) == 0:
            return {
                "is_playing": False,
                "is_paused": music_is_paused,
                "current_song": None,
                "position": None,
                "repeat": repeat_is_on,
                "playlist_size": 0,
            }

        current_song = current_playlist[current_song_index]

        player_error = None
        try:
            is_playing = (
                player_ready
                and playlist_is_active
                and bool(_player.is_playing())
            )
        except Exception as exc:
            is_playing = False
            player_error = f"Could not read player status: {exc}"

        status = {
            "is_playing": is_playing,
            "is_paused": music_is_paused,
            "current_song": current_song["title"],
            "position": f"{current_song_index + 1} of {len(current_playlist)}",
            "repeat": repeat_is_on,
            "playlist_size": len(current_playlist),
        }

        if player_error:
            status["error"] = player_error

        return status


def play_current_song():
    global playlist_is_active
    global music_is_paused

    with state_lock:
        if not initialize_player():
            return PLAYER_UNAVAILABLE

        if len(current_playlist) == 0:
            playlist_is_active = False
            music_is_paused = False
            return "No songs in the current playlist."

        song = current_playlist[current_song_index]

        if not os.path.exists(song["file"]):
            playlist_is_active = False
            music_is_paused = False
            return f"Song file not found: {song['file']}"

        try:
            media = _instance.media_new(song["file"])
            _player.set_media(media)
            play_result = _player.play()
        except Exception as exc:
            playlist_is_active = False
            music_is_paused = False
            return f"Could not play {song['title']}: {exc}"

        if play_result == -1:
            playlist_is_active = False
            music_is_paused = False
            return f"Could not play {song['title']}."

        playlist_is_active = True
        music_is_paused = False
        return f"Now playing: {song['title']}"


def start_playlist(songs, start_index=0, shuffle=False):
    global current_song_index
    global playlist_is_active
    global music_is_paused

    with state_lock:
        if len(songs) == 0:
            return "No songs in the current playlist."

        if not isinstance(start_index, int) or isinstance(start_index, bool):
            return "Invalid starting song."

        if start_index < 0 or start_index >= len(songs):
            return "Invalid starting song."

        if not initialize_player():
            return PLAYER_UNAVAILABLE

        current_playlist.clear()
        current_playlist.extend(songs)

        if shuffle:
            random.shuffle(current_playlist)
            start_index = 0

        current_song_index = start_index
        playlist_is_active = False
        music_is_paused = False

        return play_current_song()


def play_playlist(shuffle=False):
    songs = scan_library()

    if len(songs) == 0:
        return "No audio files in the library folder yet."

    return start_playlist(songs, shuffle=shuffle)


def play_song_by_title(title):
    songs = scan_library()

    for index, song in enumerate(songs):
        if song["title"].lower() == title.lower():
            return start_playlist(songs, start_index=index)

    return "That song was not found."


def song_has_ended():
    with state_lock:
        if not player_ready or _player is None or vlc is None:
            return False

        try:
            return _player.get_state() == vlc.State.Ended
        except Exception:
            logger.exception("Could not read VLC playback state")
            return False


def advance_playlist_if_needed():
    """Advance after a completed track and stop safely after VLC errors."""
    global current_song_index
    global playlist_is_active

    with state_lock:
        if (
            not playlist_is_active
            or len(current_playlist) == 0
            or music_is_paused
            or not player_ready
            or _player is None
            or vlc is None
        ):
            return None, None

        try:
            player_state = _player.get_state()
        except Exception as exc:
            playlist_is_active = False
            return "error", f"Could not read playback state: {exc}"

        if player_state == vlc.State.Error:
            playlist_is_active = False
            title = current_playlist[current_song_index]["title"]
            return "error", f"Playback failed: {title}"

        if player_state != vlc.State.Ended:
            return None, None

        current_song_index += 1

        if current_song_index >= len(current_playlist):
            if not repeat_is_on:
                current_playlist.clear()
                current_song_index = 0
                playlist_is_active = False
                return "info", "Playlist finished."
            current_song_index = 0

        message = play_current_song()
        level = "info" if playlist_is_active else "error"
        return level, message


def watch_playlist():
    global playlist_is_active

    while not shutdown_event.wait(1):
        try:
            level, message = advance_playlist_if_needed()
            if message:
                getattr(logger, level)("%s", message)
        except Exception:
            with state_lock:
                playlist_is_active = False
            logger.exception("Playlist watcher stopped playback after an unexpected error")


def start_playlist_watcher():
    global playlist_thread

    with state_lock:
        initialize_player()

        if playlist_thread is not None and playlist_thread.is_alive():
            return

        shutdown_event.clear()
        playlist_thread = threading.Thread(
            target=watch_playlist,
            name="jukebox-playlist-watcher",
            daemon=True,
        )
        playlist_thread.start()


def resume_music():
    global music_is_paused

    with state_lock:
        if not player_ready:
            return PLAYER_UNAVAILABLE

        if not music_is_paused:
            return "Music is not paused."

        try:
            _player.set_pause(0)
        except Exception as exc:
            return f"Could not resume music: {exc}"
        music_is_paused = False

        return "Music resumed"


def pause_music():
    global playlist_is_active
    global music_is_paused

    with state_lock:
        if not player_ready:
            return PLAYER_UNAVAILABLE

        if len(current_playlist) == 0 or not playlist_is_active:
            return "Nothing is playing."

        if music_is_paused:
            return "Music is already paused."

        try:
            player_state = _player.get_state()
            if player_state in (vlc.State.Ended, vlc.State.Error):
                playlist_is_active = False
                return "Nothing is playing."
            _player.set_pause(1)
        except Exception as exc:
            return f"Could not pause music: {exc}"
        music_is_paused = True

        return "Music paused."


def stop_music():
    global current_song_index
    global playlist_is_active
    global music_is_paused

    with state_lock:
        stop_error = None
        if player_ready and _player is not None:
            try:
                _player.stop()
            except Exception as exc:
                stop_error = f"Could not stop music: {exc}"

        current_playlist.clear()
        current_song_index = 0
        playlist_is_active = False
        music_is_paused = False

        if stop_error:
            return stop_error

        if not player_ready:
            return PLAYER_UNAVAILABLE

        return "Music stopped"


def next_song():
    global current_song_index
    global playlist_is_active
    global music_is_paused

    with state_lock:
        if len(current_playlist) == 0:
            return "No playlist is currently playing."

        if not player_ready:
            return PLAYER_UNAVAILABLE

        current_song_index += 1

        if current_song_index >= len(current_playlist):
            current_song_index = 0

        playlist_is_active = True
        music_is_paused = False

        return play_current_song()


def previous_song():
    global current_song_index
    global playlist_is_active
    global music_is_paused

    with state_lock:
        if len(current_playlist) == 0:
            return "No playlist is currently playing."

        if not player_ready:
            return PLAYER_UNAVAILABLE

        current_song_index -= 1

        if current_song_index < 0:
            current_song_index = len(current_playlist) - 1

        playlist_is_active = True
        music_is_paused = False

        return play_current_song()


def set_repeat(enabled):
    global repeat_is_on

    with state_lock:
        repeat_is_on = enabled

        if enabled:
            return "Repeat is on. The playlist will loop."

        return "Repeat is off."


def shutdown_player():
    """Stop the watcher and release native VLC resources."""
    global _instance
    global _player
    global player_ready
    global playlist_is_active
    global music_is_paused

    shutdown_event.set()

    thread = playlist_thread
    if (
        thread is not None
        and thread.is_alive()
        and thread is not threading.current_thread()
    ):
        thread.join(timeout=2)

    with state_lock:
        player = _player
        instance = _instance

        if player is not None:
            try:
                player.stop()
            except Exception:
                logger.exception("Could not stop VLC during shutdown")
            try:
                player.release()
            except Exception:
                logger.exception("Could not release VLC player")

        if instance is not None:
            try:
                instance.release()
            except Exception:
                logger.exception("Could not release VLC instance")

        _player = None
        _instance = None
        player_ready = False
        playlist_is_active = False
        music_is_paused = False
