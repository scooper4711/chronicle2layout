"""Tests for shared.path_validation module."""

import os
from pathlib import Path

import pytest

from shared.path_validation import reject_control_chars, user_path


class TestRejectControlChars:
    """Tests for reject_control_chars."""

    def test_accepts_normal_path(self):
        reject_control_chars("/home/user/documents/file.txt")

    def test_accepts_path_with_spaces(self):
        reject_control_chars("/home/user/my documents/file name.pdf")

    def test_accepts_path_with_special_chars(self):
        reject_control_chars("/data/reports-2024/Q1 (final).csv")

    def test_accepts_empty_string(self):
        reject_control_chars("")

    def test_rejects_null_byte(self):
        with pytest.raises(ValueError, match="U\\+0000"):
            reject_control_chars("/home/user/file\x00.txt")

    def test_rejects_newline(self):
        with pytest.raises(ValueError, match="U\\+000A"):
            reject_control_chars("/home/user/file\n.txt")

    def test_rejects_carriage_return(self):
        with pytest.raises(ValueError, match="U\\+000D"):
            reject_control_chars("/home/user/file\r.txt")

    def test_rejects_tab(self):
        with pytest.raises(ValueError, match="U\\+0009"):
            reject_control_chars("/home/user/file\t.txt")

    def test_rejects_delete_char(self):
        with pytest.raises(ValueError, match="U\\+007F"):
            reject_control_chars("/home/user/file\x7f.txt")

    def test_rejects_bell_char(self):
        with pytest.raises(ValueError, match="U\\+0007"):
            reject_control_chars("/home/user/\x07file.txt")

    def test_custom_label_in_error_message(self):
        with pytest.raises(ValueError, match="Invalid directory"):
            reject_control_chars("bad\x00path", label="directory")


class TestUserPath:
    """Tests for user_path."""

    def test_resolves_relative_path(self, tmp_path):
        target = tmp_path / "subdir" / "file.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()

        result = user_path(target)

        assert result.is_absolute()
        assert result == target.resolve()

    def test_resolves_dot_components(self, tmp_path):
        target = tmp_path / "a" / ".." / "b"
        (tmp_path / "b").mkdir()

        result = user_path(target)

        assert ".." not in result.parts
        assert result == (tmp_path / "b").resolve()

    def test_expands_tilde(self, monkeypatch):
        home = Path.home()
        result = user_path(Path("~/somefile.txt"))

        assert result == (home / "somefile.txt").resolve()

    def test_rejects_path_with_null_byte(self):
        with pytest.raises(ValueError, match="control character"):
            user_path(Path("/tmp/evil\x00file"))

    def test_rejects_path_with_newline(self):
        with pytest.raises(ValueError, match="control character"):
            user_path(Path("/tmp/evil\nfile"))

    def test_returns_path_object(self, tmp_path):
        result = user_path(tmp_path)

        assert isinstance(result, Path)

    def test_nonexistent_path_still_resolves(self, tmp_path):
        target = tmp_path / "does_not_exist"

        result = user_path(target)

        assert result.is_absolute()
        assert result.name == "does_not_exist"
