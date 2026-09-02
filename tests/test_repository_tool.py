from pathlib import Path

import pytest

from eip.repository.tool import RepositoryTool


def test_list_files_returns_repository_files(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('hello')")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text("debug: true")

    tool = RepositoryTool(tmp_path)

    files = tool.list_files()

    assert "app.py" in files
    assert "config" in files
    assert "config/settings.yaml" in files


def test_list_files_rejects_path_outside_repository(tmp_path: Path):
    tool = RepositoryTool(tmp_path)

    with pytest.raises(ValueError):
        tool.list_files("../")


def test_read_file_returns_file_contents(tmp_path: Path):
    (tmp_path / "test.txt").write_text("hello world")

    tool = RepositoryTool(tmp_path)

    content = tool.read_file("test.txt")

    assert content == "hello world"


def test_read_file_rejects_path_outside_repository(tmp_path: Path):
    tool = RepositoryTool(tmp_path)

    with pytest.raises(ValueError):
        tool.read_file("../../../etc/passwd")


def test_read_file_rejects_directory(tmp_path: Path):
    (tmp_path / "subdir").mkdir()

    tool = RepositoryTool(tmp_path)

    with pytest.raises(ValueError):
        tool.read_file("subdir")
