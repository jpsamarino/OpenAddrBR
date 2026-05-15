"""Tests for CLI commands."""

import pytest

from openaddrbr.cli._commands import _update_env_file


def test_update_env_file_new_file(tmp_path):
    """Test creating new .env file."""
    env_path = tmp_path / ".env"

    _update_env_file("pytorch-compiled", env_path)

    assert env_path.exists()
    content = env_path.read_text(encoding="utf-8")
    assert "OPENADDRBR_BACKEND=pytorch-compiled" in content
    assert "OPENADDRBR_BATCH_SIZE=16" in content


def test_update_env_file_preserves_existing_content(tmp_path):
    """Test updating existing .env without deleting other content."""
    env_path = tmp_path / ".env"
    env_path.write_text(
        "DATABASE_URL=postgres://localhost/db\nOTHER_VAR=value\nOPENADDRBR_BACKEND=onnx\n\n",
        encoding="utf-8",
    )

    _update_env_file("pytorch-compiled", env_path)

    content = env_path.read_text(encoding="utf-8")
    assert "DATABASE_URL=postgres://localhost/db" in content
    assert "OTHER_VAR=value" in content
    assert "OPENADDRBR_BACKEND=onnx" in content
    assert "OPENADDRBR_BATCH_SIZE=16" in content


def test_update_env_file_adds_new_vars(tmp_path):
    """Test adding new OPENADDRBR vars when none exist."""
    env_path = tmp_path / ".env"
    env_path.write_text("DATABASE_URL=postgres://localhost/db\n", encoding="utf-8")

    _update_env_file("cuda", env_path)

    content = env_path.read_text(encoding="utf-8")
    assert "DATABASE_URL=postgres://localhost/db" in content
    assert "OPENADDRBR_BACKEND=cuda" in content
    assert "OPENADDRBR_BATCH_SIZE=16" in content


def test_update_env_file_preserves_existing_var(tmp_path, capsys):
    """Test that existing OPENADDRBR vars are preserved and not overwritten."""
    env_path = tmp_path / ".env"
    env_path.write_text(
        "OPENADDRBR_BACKEND=onnx-int8\nOPENADDRBR_BATCH_SIZE=8\n",
        encoding="utf-8",
    )

    _update_env_file("pytorch", env_path)

    content = env_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    backend_lines = [l for l in lines if l.startswith("OPENADDRBR_BACKEND=")]
    assert len(backend_lines) == 1
    assert backend_lines[0] == "OPENADDRBR_BACKEND=onnx-int8"
    batch_lines = [l for l in lines if l.startswith("OPENADDRBR_BATCH_SIZE=")]
    assert len(batch_lines) == 1
    assert batch_lines[0] == "OPENADDRBR_BATCH_SIZE=8"
    captured = capsys.readouterr()
    assert "OPENADDRBR_BACKEND" in captured.out
    assert "OPENADDRBR_BATCH_SIZE" in captured.out
