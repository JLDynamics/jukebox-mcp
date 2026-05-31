import json
import os
import random
import shutil
import threading
import time

import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONGS_FILE = os.path.join(BASE_DIR, "songs.json")
INBOX_DIR = os.path.join(BASE_DIR, "inbox")
LIBRARY_DIR = os.path.join(BASE_DIR, "library")

pygame.mixer.init()

current_playlist = []
current_song_index = 0
playlist_is_active = False
music_is_paused = False


def get_player_status():
    if len(current_playlist) == 0:
        return {
            "is_playing": False,
            "is_paused": music_is_paused,
            "crrent_song": None,
            "playlist_size": 0,
        }

    current_song = current_playlist[current_song_index]

    return {
        "is_playing": pygame.mixer.music.get_busy(),
        "is_paused": music_is_paused,
        "current_song": current_song["title"],
        "playlist_size": len(current_playlist),
    }


def list_inbox_mp3_files():
    mp3_files = []

    for file_name in os.listdir(INBOX_DIR):
        if file_name.endswith(".mp3"):
            mp3_files.append(file_name)

    return mp3_files


def import_song_from_inbox(file_name, mood):
    songs = load_songs()

    if mood not in songs:
        return "That mood does not exist."

    old_path = os.path.join(INBOX_DIR, file_name)
    new_path = os.path.join(LIBRARY_DIR, mood, file_name)
    saved_path = os.path.join("library", mood, file_name)

    if not os.path.exists(old_path):
        return "that file does not exist in inbox."

    os.makedirs(os.path.join(LIBRARY_DIR, mood), exist_ok=True)

    shutil.move(old_path, new_path)

    song_info = {
        "title": os.path.splitext(file_name)[0],
        "file": saved_path.replace("\\", "/"),
    }

    songs[mood].append(song_info)
    save_songs(songs)

    return f"{file_name} is ready to import into {mood}."


def delete_song(mood, title):
    songs = load_songs()

    if mood not in songs:
        return "that mood does not exist."

    for song in songs[mood]:
        if song["title"].lower() == title.lower():
            song_path = os.path.join(BASE_DIR, song["file"])

            songs[mood].remove(song)
            save_songs(songs)

            if os.path.exists(song_path):
                os.remove(song_path)
                return f"{title} deleted from songs.json and library."

            return f"{title} deleted from songs.json, but mp3 file was not found."

        return "that song was not found in this mood"


def play_current_song():
    global current_song_index

    if len(current_playlist) == 0:
        return "No songs in the current playlist."

    song = current_playlist[current_song_index]
    song_path = os.path.join(BASE_DIR, song["file"])

    if os.path.exists(song_path):
        pygame.mixer.music.load(song_path)
        pygame.mixer.music.play()
        return f"Now playing: {song['title']}"

    return f"Song file not found:{song_path}"


def play_mood_playlist(mood):

    global current_song_index
    global playlist_is_active
    global music_is_paused

    songs = load_songs()

    if mood not in songs:
        return "That mood does not exist."

    if len(songs[mood]) == 0:
        return "No songs saved for this mood yet."

    current_playlist.clear()

    for song in songs[mood]:
        current_playlist.append(song)

    current_song_index = 0
    playlist_is_active = True
    music_is_paused = False

    return play_current_song()


def shuffle_mood_playlist(mood):
    global current_song_index
    global playlist_is_active
    global music_is_paused

    songs = load_songs()

    if mood not in songs:
        return "That mood does not exist."

    if len(songs[mood]) == 0:
        return "No songs saved for this mood yet."

    current_playlist.clear()

    for song in songs[mood]:
        current_playlist.append(song)

    random.shuffle(current_playlist)

    current_song_index = 0
    playlist_is_active = True
    music_is_paused = False

    return play_current_song()


def watch_playlist():
    global current_song_index
    global playlist_is_active

    while True:
        time.sleep(1)

        if playlist_is_active and len(current_playlist) > 0 and not music_is_paused:
            if not pygame.mixer.music.get_busy():
                current_song_index += 1

                if current_song_index >= len(current_playlist):
                    playlist_is_active = False
                    print("\nPlaylist finished.")
                else:
                    message = play_current_song()
                    print(message)


playlist_thread = threading.Thread(target=watch_playlist, daemon=True)
playlist_thread.start()


def resume_music():
    global music_is_paused

    pygame.mixer.music.unpause()
    music_is_paused = False

    return "Music resumed"


def pause_music():
    global music_is_paused

    pygame.mixer.music.pause()
    music_is_paused = True

    return "Music paused."


def stop_music():
    global playlist_is_active
    global music_is_paused

    pygame.mixer.music.stop()
    playlist_is_active = False
    music_is_paused = False

    return "Music stopped"


def next_song():
    global current_song_index

    if len(current_playlist) == 0:
        return "No playlist is currently playing."

    current_song_index += 1

    if current_song_index >= len(current_playlist):
        current_song_index = 0

    return play_current_song()


def load_songs():
    try:
        with open(SONGS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {
            "happy": [],
            "sad": [],
            "focused": [],
            "angry": [],
        }


def save_songs(songs):
    with open(SONGS_FILE, "w") as file:
        json.dump(songs, file, indent=4)


def list_moods():
    songs = load_songs()
    return list(songs.keys())


def list_songs(mood):
    songs = load_songs()

    if mood not in songs:
        return None

    return songs[mood]
