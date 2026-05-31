import json
import os
import random
import shutil
import threading
import time

import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
pygame.mixer.init()

current_playlist = []
current_song_index = 0
playlist_is_active = False
music_is_paused = False

try:
    with open(os.path.join(BASE_DIR, "songs.json"), "r") as file:
        songs = json.load(file)
except FileNotFoundError:
    songs = {
        "happy": [],
        "sad": [],
        "focused": [],
        "angry": [],
    }


def play_current_song():
    global current_song_index

    if len(current_playlist) == 0:
        print("No songs in the current playlist.")
        return

    song = current_playlist[current_song_index]
    song_path = os.path.join(BASE_DIR, song["file"])

    if os.path.exists(song_path):
        pygame.mixer.music.load(song_path)
        pygame.mixer.music.play()
        print(f"Now playing: {song['title']}")
    else:
        print("Song file not found:")
        print(song_path)


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
                    play_current_song()


playlist_thread = threading.Thread(target=watch_playlist, daemon=True)
playlist_thread.start()


while True:
    print("\nPersonal Music Playlist Maker")
    print("1. Get songs by mood")
    print("2. View all moods")
    print("3. Delete song from mood")
    print("4. Play MP3 song")
    print("5. Import MP3 files from inbox")
    print("6. Play mood playlist")
    print("7. Shuffle mood playlist")
    print("8. Pause")
    print("9. Resume")
    print("10. Stop")
    print("11. Next song")
    print("12. Exit")

    choice = input("choose an option: ")

    if choice == "1":
        mood = input("What mood are you in? ").lower()

        if mood in songs:
            print("Here are songs for your mood:")
            if len(songs[mood]) == 0:
                print("No songs saved for this mood yet.")
            else:
                for song in songs[mood]:
                    print("_", song["title"])
        else:
            print("Sorry, i do not have songs for that mood.")

    elif choice == "2":
        print("Available moods:")
        for mood in songs:
            print("_", mood)

    elif choice == "3":
        mood = input("Which mood is the song in? ").lower()

        if mood not in songs:
            print("That mood does not exist.")
        elif len(songs[mood]) == 0:
            print("No songs saved for this mood yet.")
        else:
            for i, song in enumerate(songs[mood], start=1):
                print(f"{i}. {song['title']}")

            song_number = input("Choose a song number to delete: ")

            if song_number.isdigit():
                song_number = int(song_number)

                if song_number >= 1 and song_number <= len(songs[mood]):
                    removed_song = songs[mood].pop(song_number - 1)
                    removed_song_path = os.path.join(BASE_DIR, removed_song["file"])

                    with open(os.path.join(BASE_DIR, "songs.json"), "w") as file:
                        json.dump(songs, file, indent=4)

                    if os.path.exists(removed_song_path):
                        os.remove(removed_song_path)
                        print(
                            f"{removed_song['title']} deleted from songs.json and library."
                        )
                    else:
                        print(f"{removed_song['title']} deleted from songs.json.")
                        print("MP3 file was not found in the library.")
                else:
                    print("Invalid song number.")
            else:
                print("Please enter a number.")

    elif choice == "4":
        playlist_is_active = False
        music_is_paused = False
        mood = input("Which mood do you want to play from? ").lower()

        if mood not in songs:
            print("That mood does not exist.")
        elif len(songs[mood]) == 0:
            print("No songs saved for this mood yet.")
        else:
            print("Available MP3 songs:")
            for i, song in enumerate(songs[mood], start=1):
                print(f"{i}. {song['title']}")

            song_number = input("Choose a song number: ")

            if song_number.isdigit():
                song_number = int(song_number)

                if song_number >= 1 and song_number <= len(songs[mood]):
                    current_playlist.clear()
                    current_playlist.append(songs[mood][song_number - 1])
                    current_song_index = 0
                    play_current_song()
                else:
                    print("Invalid song number.")
            else:
                print("Please enter a number.")

    elif choice == "5":
        mp3_files = []
        inbox_path = os.path.join(BASE_DIR, "inbox")

        for file_name in os.listdir(inbox_path):
            if file_name.endswith(".mp3"):
                mp3_files.append(file_name)

        if len(mp3_files) == 0:
            print("No MP3 files found in inbox.")
        else:
            print("MP3 files found in inbox:")
            for file_name in mp3_files:
                print("_", file_name)

            for file_name in mp3_files:
                mood = input(f"Which mood for {file_name}? ").lower()

                if mood in songs:
                    old_path = os.path.join(BASE_DIR, "inbox", file_name)
                    new_path = os.path.join(BASE_DIR, "library", mood, file_name)
                    saved_path = os.path.join("library", mood, file_name)
                    title = os.path.splitext(file_name)[0]

                    os.makedirs(os.path.join(BASE_DIR, "library", mood), exist_ok=True)
                    shutil.move(old_path, new_path)

                    song_info = {
                        "title": title,
                        "file": saved_path.replace("\\", "/"),
                    }

                    songs[mood].append(song_info)

                    with open(os.path.join(BASE_DIR, "songs.json"), "w") as file:
                        json.dump(songs, file, indent=4)

                    print(f"{file_name} moved to library/{mood}/ and saved.")
                else:
                    print("Invalid mood.")

    elif choice == "6":
        mood = input("which mood playlist do you want to play? ").lower()

        if mood not in songs:
            print("that mood does not exist.")
        elif len(songs[mood]) == 0:
            print("No songs saved for this mood yet.")
        else:
            current_playlist.clear()

            for song in songs[mood]:
                current_playlist.append(song)

            current_song_index = 0
            playlist_is_active = True
            music_is_paused = False
            play_current_song()

    elif choice == "7":
        mood = input("which mood playlist do you want to shuffle? ").lower()

        if mood not in songs:
            print("That mood does not exist.")
        elif len(songs[mood]) == 0:
            print("No songs saved for this mood yet.")
        else:
            current_playlist.clear()

            for song in songs[mood]:
                current_playlist.append(song)

            random.shuffle(current_playlist)
            current_song_index = 0
            playlist_is_active = True
            music_is_paused = False
            play_current_song()

    elif choice == "8":
        pygame.mixer.music.pause()
        music_is_paused = True
        print("music paused.")

    elif choice == "9":
        pygame.mixer.music.unpause()
        music_is_paused = False
        print("Music resumed")

    elif choice == "10":
        pygame.mixer.music.stop()
        playlist_is_active = False
        music_is_paused = False
        print("Music stopped.")

    elif choice == "11":
        if len(current_playlist) == 0:
            print("No playlist is currently playing.")
        else:
            current_song_index += 1

            if current_song_index >= len(current_playlist):
                current_song_index = 0

            play_current_song()

    elif choice == "12":
        playlist_is_active = False
        music_is_paused = False
        pygame.mixer.music.stop()
        print("Goodbye!")
        break

    else:
        print("invalid choice. Try again.")
