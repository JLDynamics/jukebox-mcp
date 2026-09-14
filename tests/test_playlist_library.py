import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import playlist_library as library


class FakeState:
    Ended = "ended"
    Error = "error"
    Playing = "playing"


class FakeVLC:
    State = FakeState


class FakeInstance:
    def __init__(self):
        self.media_paths = []
        self.released = False

    def media_new(self, path):
        self.media_paths.append(path)
        return path

    def release(self):
        self.released = True


class FakePlayer:
    def __init__(self, *, state=FakeState.Playing, play_result=0):
        self.state = state
        self.play_result = play_result
        self.media = None
        self.pause_values = []
        self.stopped = False
        self.released = False

    def get_state(self):
        return self.state

    def is_playing(self):
        return self.state == FakeState.Playing

    def set_media(self, media):
        self.media = media

    def play(self):
        return self.play_result

    def set_pause(self, value):
        self.pause_values.append(value)

    def stop(self):
        self.stopped = True

    def release(self):
        self.released = True


class PlaylistLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.instance = FakeInstance()
        self.player = FakePlayer()

        self.patchers = [
            mock.patch.object(library, "LIBRARY_DIR", self.temp_dir.name),
            mock.patch.object(library, "vlc", FakeVLC),
            mock.patch.object(library, "_instance", self.instance),
            mock.patch.object(library, "_player", self.player),
            mock.patch.object(library, "player_ready", True),
        ]
        for patcher in self.patchers:
            patcher.start()

        with library.state_lock:
            library.current_playlist.clear()
            library.current_song_index = 0
            library.playlist_is_active = False
            library.music_is_paused = False
            library.repeat_is_on = False

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temp_dir.cleanup()

    def add_song(self, name):
        path = os.path.join(self.temp_dir.name, name)
        with open(path, "wb"):
            pass
        return path

    def test_scan_library_sorts_supported_files_and_ignores_other_entries(self):
        self.add_song("Zulu.MP3")
        self.add_song("alpha.flac")
        self.add_song("notes.txt")
        os.mkdir(os.path.join(self.temp_dir.name, "nested.mp3"))

        self.assertEqual(library.get_library(), ["Zulu", "alpha"])

    def test_scan_library_reports_filesystem_errors_clearly(self):
        with (
            mock.patch.object(library.os, "listdir", side_effect=OSError("denied")),
            self.assertRaisesRegex(RuntimeError, "Could not scan library folder: denied"),
        ):
            library.scan_library()

    def test_invalid_start_index_is_rejected_before_playlist_is_changed(self):
        song = {"title": "song", "file": self.add_song("song.mp3")}

        result = library.start_playlist([song], start_index=2)

        self.assertEqual(result, "Invalid starting song.")
        self.assertEqual(library.current_playlist, [])
        self.assertFalse(library.playlist_is_active)

    def test_initialize_releases_instance_when_player_creation_returns_none(self):
        partial_instance = mock.Mock()
        partial_instance.media_player_new.return_value = None
        fake_vlc = mock.Mock()
        fake_vlc.Instance.return_value = partial_instance

        with (
            mock.patch.object(library, "vlc", fake_vlc),
            mock.patch.object(library, "_instance", None),
            mock.patch.object(library, "_player", None),
            mock.patch.object(library, "player_ready", False),
        ):
            self.assertFalse(library.initialize_player())
            self.assertIsNone(library._instance)
            self.assertIsNone(library._player)

        partial_instance.release.assert_called_once_with()

    def test_initialize_releases_instance_when_player_creation_raises(self):
        partial_instance = mock.Mock()
        partial_instance.media_player_new.side_effect = RuntimeError("player failure")
        fake_vlc = mock.Mock()
        fake_vlc.Instance.return_value = partial_instance

        with (
            mock.patch.object(library, "vlc", fake_vlc),
            mock.patch.object(library, "_instance", None),
            mock.patch.object(library, "_player", None),
            mock.patch.object(library, "player_ready", False),
            mock.patch.object(library.logger, "exception"),
        ):
            self.assertFalse(library.initialize_player())
            self.assertIsNone(library._instance)
            self.assertIsNone(library._player)

        partial_instance.release.assert_called_once_with()

    def test_import_does_not_start_the_watcher(self):
        self.assertIsNone(library.playlist_thread)

    def test_failed_vlc_start_does_not_leave_playlist_active(self):
        self.add_song("broken.mp3")
        self.player.play_result = -1

        result = library.play_playlist()

        self.assertEqual(result, "Could not play broken.")
        self.assertFalse(library.playlist_is_active)
        self.assertFalse(library.music_is_paused)

    def test_playback_exception_is_returned_without_escaping(self):
        self.add_song("broken.mp3")
        self.player.play = mock.Mock(side_effect=RuntimeError("VLC failure"))

        result = library.play_playlist()

        self.assertEqual(result, "Could not play broken: VLC failure")
        self.assertFalse(library.playlist_is_active)

    def test_pause_exception_does_not_claim_music_was_paused(self):
        self.add_song("song.mp3")
        library.play_playlist()
        self.player.set_pause = mock.Mock(side_effect=RuntimeError("pause failure"))

        result = library.pause_music()

        self.assertEqual(result, "Could not pause music: pause failure")
        self.assertFalse(library.music_is_paused)

    def test_pause_does_not_freeze_playlist_after_track_has_ended(self):
        self.add_song("song.mp3")
        library.play_playlist()
        self.player.state = FakeState.Ended

        result = library.pause_music()

        self.assertEqual(result, "Nothing is playing.")
        self.assertFalse(library.playlist_is_active)
        self.assertFalse(library.music_is_paused)

    def test_stop_clears_status_and_prevents_next_from_restarting(self):
        self.add_song("song.mp3")
        library.play_playlist()

        self.assertEqual(library.stop_music(), "Music stopped")

        self.assertEqual(library.current_playlist, [])
        self.assertEqual(library.get_player_status()["current_song"], None)
        self.assertEqual(library.next_song(), "No playlist is currently playing.")

    def test_next_and_previous_wrap_while_playlist_is_loaded(self):
        first = self.add_song("first.mp3")
        second = self.add_song("second.mp3")
        library.current_playlist.extend(
            [{"title": "first", "file": first}, {"title": "second", "file": second}]
        )
        library.current_song_index = 1

        self.assertEqual(library.next_song(), "Now playing: first")
        self.assertEqual(library.previous_song(), "Now playing: second")

    def test_repeat_restarts_playlist_after_last_song_ends(self):
        song = self.add_song("song.mp3")
        library.current_playlist.append({"title": "song", "file": song})
        library.playlist_is_active = True
        library.repeat_is_on = True
        self.player.state = FakeState.Ended

        level, message = library.advance_playlist_if_needed()

        self.assertEqual((level, message), ("info", "Now playing: song"))
        self.assertEqual(library.current_song_index, 0)
        self.assertTrue(library.playlist_is_active)

    def test_repeat_off_marks_playlist_finished_after_last_song(self):
        song = self.add_song("song.mp3")
        library.current_playlist.append({"title": "song", "file": song})
        library.playlist_is_active = True
        self.player.state = FakeState.Ended

        level, message = library.advance_playlist_if_needed()

        self.assertEqual((level, message), ("info", "Playlist finished."))
        self.assertFalse(library.playlist_is_active)
        self.assertEqual(library.current_song_index, 0)
        self.assertEqual(library.current_playlist, [])
        self.assertEqual(library.get_player_status()["current_song"], None)

    def test_auto_advance_moves_to_next_song_after_ended_state(self):
        first = self.add_song("first.mp3")
        second = self.add_song("second.mp3")
        library.current_playlist.extend(
            [{"title": "first", "file": first}, {"title": "second", "file": second}]
        )
        library.playlist_is_active = True
        self.player.state = FakeState.Ended

        level, message = library.advance_playlist_if_needed()

        self.assertEqual(level, "info")
        self.assertEqual(message, "Now playing: second")
        self.assertEqual(library.current_song_index, 1)

    def test_vlc_error_stops_auto_advance_instead_of_skipping(self):
        song = self.add_song("broken.mp3")
        library.current_playlist.append({"title": "broken", "file": song})
        library.playlist_is_active = True
        library.repeat_is_on = True
        self.player.state = FakeState.Error

        level, message = library.advance_playlist_if_needed()

        self.assertEqual(level, "error")
        self.assertEqual(message, "Playback failed: broken")
        self.assertFalse(library.playlist_is_active)

    def test_song_has_ended_is_safe_when_player_is_unavailable(self):
        library.player_ready = False
        library._player = None

        self.assertFalse(library.song_has_ended())

    def test_status_reports_vlc_query_errors_without_raising(self):
        self.add_song("song.mp3")
        library.play_playlist()
        self.player.is_playing = mock.Mock(side_effect=RuntimeError("status failure"))

        status = library.get_player_status()

        self.assertFalse(status["is_playing"])
        self.assertEqual(status["error"], "Could not read player status: status failure")

    def test_watcher_logs_without_writing_to_stdout(self):
        fake_event = mock.Mock()
        fake_event.wait.side_effect = [False, True]
        stdout = io.StringIO()

        with (
            mock.patch.object(library, "shutdown_event", fake_event),
            mock.patch.object(
                library,
                "advance_playlist_if_needed",
                return_value=("info", "Playlist finished."),
            ),
            mock.patch.object(library.logger, "info") as log_info,
            contextlib.redirect_stdout(stdout),
        ):
            library.watch_playlist()

        self.assertEqual(stdout.getvalue(), "")
        log_info.assert_called_once_with("%s", "Playlist finished.")

    def test_shutdown_stops_watcher_and_releases_vlc(self):
        fake_thread = mock.Mock()
        fake_thread.is_alive.return_value = True

        with mock.patch.object(library, "playlist_thread", fake_thread):
            library.shutdown_player()

        fake_thread.join.assert_called_once()
        self.assertTrue(self.player.stopped)
        self.assertTrue(self.player.released)
        self.assertTrue(self.instance.released)


if __name__ == "__main__":
    unittest.main()
