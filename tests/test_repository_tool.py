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


def test_search_code_finds_matches(tmp_path: Path):
    (tmp_path / "app.py").write_text("def hello():\n    return 42\n")
    (tmp_path / "config.py").write_text("DEBUG = True\n")

    tool = RepositoryTool(tmp_path)

    results = tool.search_code("hello")

    assert len(results) == 1
    assert results[0]["file"] == "app.py"
    assert results[0]["line_number"] == 1
    assert results[0]["line_text"] == "def hello():"


def test_search_code_returns_multiple_matches(tmp_path: Path):
    (tmp_path / "app.py").write_text("hello\nhello\nhello\n")

    tool = RepositoryTool(tmp_path)

    results = tool.search_code("hello")

    assert len(results) == 3
    assert all(r["file"] == "app.py" for r in results)
    assert results[0]["line_number"] == 1
    assert results[1]["line_number"] == 2
    assert results[2]["line_number"] == 3


def test_search_code_respects_max_results(tmp_path: Path):
    (tmp_path / "file.txt").write_text("match\n" * 50)

    tool = RepositoryTool(tmp_path)

    results = tool.search_code("match", max_results=10)

    assert len(results) == 10


def test_search_code_ignores_excluded_directories(tmp_path: Path):
    (tmp_path / "app.py").write_text("data")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("data")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cache.py").write_text("data")

    tool = RepositoryTool(tmp_path)

    results = tool.search_code("data")

    assert len(results) == 1
    assert results[0]["file"] == "app.py"


def test_search_code_handles_binary_files(tmp_path: Path):
    (tmp_path / "app.py").write_text("hello")
    (tmp_path / "binary.pyc").write_bytes(b"\x80\x81\x82\x83hello")

    tool = RepositoryTool(tmp_path)

    results = tool.search_code("hello")

    assert len(results) == 1
    assert results[0]["file"] == "app.py"


def test_search_code_returns_no_matches(tmp_path: Path):
    (tmp_path / "app.py").write_text("hello world")

    tool = RepositoryTool(tmp_path)

    results = tool.search_code("notfound")

    assert results == []


def test_search_code_rejects_empty_query(tmp_path: Path):
    tool = RepositoryTool(tmp_path)

    with pytest.raises(ValueError):
        tool.search_code("")


def test_search_code_rejects_non_positive_max_results(tmp_path: Path):
    tool = RepositoryTool(tmp_path)

    with pytest.raises(ValueError):
        tool.search_code("test", max_results=0)

    with pytest.raises(ValueError):
        tool.search_code("test", max_results=-1)

