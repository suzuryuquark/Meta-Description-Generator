from pathlib import Path

import pytest

from scripts.package_deduplication import filter_duplicate_flet_binaries


def _binary(path: Path, destination: str, content: bytes) -> tuple[str, str, str]:
    path.write_bytes(content)
    return destination, str(path), "BINARY"


def test_filter_duplicate_flet_binaries_removes_identical_allowlisted_pair(
    tmp_path: Path,
) -> None:
    root = _binary(tmp_path / "root.dll", "libmpv-2.dll", b"same")
    canonical = _binary(
        tmp_path / "canonical.dll",
        "flet_desktop/app/flet/libmpv-2.dll",
        b"same",
    )

    filtered, removed = filter_duplicate_flet_binaries([root, canonical])

    assert filtered == [canonical]
    assert [item.root_name for item in removed] == ["libmpv-2.dll"]


def test_filter_duplicate_flet_binaries_removes_flet_plugin_pair(tmp_path: Path) -> None:
    root = _binary(tmp_path / "root.dll", "window_manager_plugin.dll", b"plugin")
    canonical = _binary(
        tmp_path / "canonical.dll",
        "flet_desktop\\app\\flet\\window_manager_plugin.dll",
        b"plugin",
    )

    filtered, _ = filter_duplicate_flet_binaries([root, canonical])

    assert filtered == [canonical]


def test_filter_duplicate_flet_binaries_keeps_non_allowlisted_runtime_pair(
    tmp_path: Path,
) -> None:
    root = _binary(tmp_path / "root.dll", "ucrtbase.dll", b"same")
    canonical = _binary(
        tmp_path / "canonical.dll",
        "flet_desktop\\app\\flet\\ucrtbase.dll",
        b"same",
    )

    filtered, removed = filter_duplicate_flet_binaries([root, canonical])

    assert filtered == [root, canonical]
    assert removed == ()


def test_filter_duplicate_flet_binaries_rejects_different_content(tmp_path: Path) -> None:
    root = _binary(tmp_path / "root.dll", "libEGL.dll", b"root")
    canonical = _binary(
        tmp_path / "canonical.dll",
        "flet_desktop\\app\\flet\\libEGL.dll",
        b"canonical",
    )

    with pytest.raises(RuntimeError, match="differ"):
        filter_duplicate_flet_binaries([root, canonical])


def test_filter_duplicate_flet_binaries_rejects_missing_canonical(tmp_path: Path) -> None:
    root = _binary(tmp_path / "root.dll", "flutter_windows.dll", b"root")

    with pytest.raises(RuntimeError, match="missing"):
        filter_duplicate_flet_binaries([root])
