import os
import random
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIBRARY_DIR = os.path.join(BASE_DIR, "library")
AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav", ".flac", ".m4a", ".aac", ".opus")

try:
    import vlc

    _instance = vlc.Instance("--intf=dummy", "--no-video")
    _player = _instance.media_player_new() if _instance else None
    player_ready = _player is not None
except Exception:
    vlc = None
    _instance = None
    _player = None
    player_ready = False

PLAYER_UNAVAILABLE = "Audio player not available. Is VLC media player installed?"

state_lock = threading.RLock()

current_playlist = []
current_song_index = 0
playlist_is_active = False
music_is_paused = False
repeat_is_on = False


def scan_library():
    """Scan the library/ folder for audio files.

    The folder on disk is the source of truth. Every audio file
    directly inside library/ is a song.
    """
    os.makedirs(LIBRARY_DIR, exist_ok=True)

    songs = []

    for file_name in sorted(os.listdir(LIBRARY_DIR)):
        if file_name.lower().endswith(AUDIO_EXTENSIONS):
            songs.append(
                {
                    "title": os.path.splitext(file_name)[0],
                    "file": os.path.join(LIBRARY_DIR, file_name),
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

        return {
            "is_playing": player_ready and bool(_player.is_playing()),
            "is_paused": music_is_paused,
            "current_song": current_song["title"],
            "position": f"{current_song_index + 1} of {len(current_playlist)}",
            "repeat": repeat_is_on,
            "playlist_size": len(current_playlist),
        }


def play_current_song():
    with state_lock:
        if not player_ready:
            return PLAYER_UNAVAILABLE

        if len(current_playlist) == 0:
            return "No songs in the current playlist."

        song = current_playlist[current_song_index]

        if not os.path.exists(song["file"]):
            return f"Song file not found: {song['file']}"

        media = _instance.media_new(song["file"])
        _player.set_media(media)

        if _player.play() == -1:
            return f"Could not play {song['title']}."

        return f"Now playing: {song['title']}"


def start_playlist(songs, start_index=0, shuffle=False):
    global current_song_index
    global playlist_is_active
    global music_is_paused

    with state_lock:
        if not player_ready:
            return PLAYER_UNAVAILABLE

        current_playlist.clear()
        current_playlist.extend(songs)

        if shuffle:
            random.shuffle(current_playlist)
            start_index = 0

        current_song_index = start_index
        playlist_is_active = True
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
    state = _player.get_state()
    return state in (vlc.State.Ended, vlc.State.Error)


def watch_playlist():
    global current_song_index
    global playlist_is_active

    while True:
        time.sleep(1)

        with state_lock:
            if (
                playlist_is_active
                and len(current_playlist) > 0
                and not music_is_paused
                and player_ready
                and song_has_ended()
            ):
                current_song_index += 1

                if current_song_index >= len(current_playlist):
                    if repeat_is_on:
                        current_song_index = 0
                        print(play_current_song())
                    else:
                        playlist_is_active = False
                        print("\nPlaylist finished.")
                else:
                    print(play_current_song())


playlist_thread = threading.Thread(target=watch_playlist, daemon=True)
playlist_thread.start()


def resume_music():
    global music_is_paused

    with state_lock:
        if not player_ready:
            return PLAYER_UNAVAILABLE

        if not music_is_paused:
            return "Music is not paused."

        _player.set_pause(0)
        music_is_paused = False

        return "Music resumed"


def pause_music():
    global music_is_paused

    with state_lock:
        if not player_ready:
            return PLAYER_UNAVAILABLE

        if len(current_playlist) == 0 or not playlist_is_active:
            return "Nothing is playing."

        if music_is_paused:
            return "Music is already paused."

        _player.set_pause(1)
        music_is_paused = True

        return "Music paused."


def stop_music():
    global playlist_is_active
    global music_is_paused

    with state_lock:
        if not player_ready:
            return PLAYER_UNAVAILABLE

        _player.stop()
        playlist_is_active = False
        music_is_paused = False

        return "Music stopped"


def next_song():
    global current_song_index
    global playlist_is_active
    global music_is_paused

    with state_lock:
        if len(current_playlist) == 0:
            return "No playlist is currently playing."

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
