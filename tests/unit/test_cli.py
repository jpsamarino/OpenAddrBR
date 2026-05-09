"""Tests for CLI - TDD approach."""

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest


class TestCLI:
    """Tests for CLI commands."""

    def test_info_command_exists(self):
        """info command should show data path and status."""
        from openaddrbr.cli._commands import _main

        with patch("openaddrbr.cli._commands.get_data_path") as mock_path:
            mock_path.return_value = Path("/test/path")

            with patch("openaddrbr.cli._commands.check_data_exists") as mock_check:
                mock_check.return_value = True

                # Call with info subcommand - should not raise
                _main(["info"])

                # Verify the functions were called
                mock_path.assert_called_once()
                mock_check.assert_called_once()

    def test_download_command_exists(self):
        """download command should exist."""
        from openaddrbr.cli._commands import _main

        with patch("openaddrbr.cli._commands.download_data") as mock_dl:
            mock_dl.return_value = Path("/test/path")

            # Call with download subcommand - should not raise
            _main(["download"])

            # Verify download was called
            mock_dl.assert_called_once()

    def test_download_with_force_flag(self):
        """download command should pass force argument."""
        from openaddrbr.cli._commands import _main

        with patch("openaddrbr.cli._commands.download_data") as mock_dl:
            mock_dl.return_value = Path("/test/path")

            _main(["download", "--force"])

            mock_dl.assert_called_once_with(force=True)

    def test_main_help(self):
        """Main command should show help."""
        from openaddrbr.cli._commands import _main

        with pytest.raises(SystemExit) as exc_info:
            _main(["--help"])
        assert exc_info.value.code == 0
