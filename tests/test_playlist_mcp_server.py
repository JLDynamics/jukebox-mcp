import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import playlist_mcp_server as server


class PlaylistMCPServerTests(unittest.TestCase):
    def test_control_player_normalizes_action_and_title(self):
        with mock.patch.object(server, "play_song_by_title", return_value="played") as play:
            result = server.control_player("  PLAY  ", title="  My Song  ")

        self.assertEqual(result, "played")
        play.assert_called_once_with("My Song")

    def test_control_player_rejects_non_text_values_when_called_directly(self):
        with self.assertRaisesRegex(TypeError, "Action must be text"):
            server.control_player(None)

        with self.assertRaisesRegex(TypeError, "Title must be text"):
            server.control_player("play", title=None)

    def test_unknown_action_raises_when_called_directly(self):
        with self.assertRaisesRegex(ValueError, "Unknown action"):
            server.control_player("dance")

    def test_main_always_shuts_down_player(self):
        with (
            mock.patch.object(server, "start_playlist_watcher") as start,
            mock.patch.object(server, "shutdown_player") as shutdown,
            mock.patch.object(server.mcp, "run", side_effect=RuntimeError("server failed")),
            self.assertRaisesRegex(RuntimeError, "server failed"),
        ):
            server.main()

        start.assert_called_once_with()
        shutdown.assert_called_once_with()

    def test_main_cleans_up_when_watcher_start_fails(self):
        with (
            mock.patch.object(
                server,
                "start_playlist_watcher",
                side_effect=RuntimeError("thread failed"),
            ),
            mock.patch.object(server, "shutdown_player") as shutdown,
            mock.patch.object(server.mcp, "run") as run,
            self.assertRaisesRegex(RuntimeError, "thread failed"),
        ):
            server.main()

        run.assert_not_called()
        shutdown.assert_called_once_with()


class PlaylistMCPStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_action_is_rejected_as_mcp_tool_error(self):
        project_dir = Path(__file__).resolve().parents[1]
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["playlist_mcp_server.py"],
            cwd=project_dir,
            env={"PYTHONDONTWRITEBYTECODE": "1"},
        )

        with open(os.devnull, "w") as error_log:
            async with stdio_client(parameters, errlog=error_log) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()

                    tools = await session.list_tools()
                    control = next(
                        tool for tool in tools.tools if tool.name == "control_player"
                    )
                    action_schema = control.inputSchema["properties"]["action"]
                    action_definition = action_schema["$ref"].rsplit("/", 1)[-1]
                    action_schema = control.inputSchema["$defs"][action_definition]
                    self.assertEqual(
                        action_schema["enum"],
                        [action.value for action in server.PlayerAction],
                    )

                    normalized = await session.call_tool(
                        "control_player",
                        {"action": "  PAUSE  "},
                    )
                    invalid = await session.call_tool(
                        "control_player",
                        {"action": "dance"},
                    )

        self.assertFalse(normalized.isError)
        self.assertTrue(invalid.isError)


if __name__ == "__main__":
    unittest.main()
