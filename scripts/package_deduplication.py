"""Safe filtering of duplicate Flet runtime binaries from PyInstaller TOCs."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

FLET_RUNTIME_PREFIX = "flet_desktop\\app\\flet\\"
FLET_ROOT_BINARY_ALLOWLIST = frozenset(
    {
        "flutter_windows.dll",
        "libegl.dll",
        "libglesv2.dll",
        "libmpv-2.dll",
        "rive_common_plugin.dll",
        "ucrtbased.dll",
    }
)

BinaryEntry = tuple[str, str, str]


@dataclass(frozen=True)
class RemovedBinary:
    root_name: str
    canonical_name: str
    size_bytes: int
    sha256: str


def _normalise_destination(name: str) -> str:
    return name.replace("/", "\\").lstrip(".\\")


def _is_removable_flet_binary(name: str) -> bool:
    normalised = _normalise_destination(name).casefold()
    return normalised in FLET_ROOT_BINARY_ALLOWLIST or normalised.endswith("_plugin.dll")


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def filter_duplicate_flet_binaries(
    binaries: Iterable[BinaryEntry],
) -> tuple[list[BinaryEntry], tuple[RemovedBinary, ...]]:
    """Remove allow-listed root binaries only when the canonical copy is identical."""
    entries = list(binaries)
    by_destination = {_normalise_destination(entry[0]).casefold(): entry for entry in entries}
    removed_destinations: set[str] = set()
    removed: list[RemovedBinary] = []

    for entry in entries:
        root_name = _normalise_destination(entry[0])
        if "\\" in root_name or not _is_removable_flet_binary(root_name):
            continue

        canonical_name = f"{FLET_RUNTIME_PREFIX}{root_name}"
        canonical_entry = by_destination.get(canonical_name.casefold())
        if canonical_entry is None:
            raise RuntimeError(
                f"Canonical Flet runtime binary is missing for root duplicate: {root_name}"
            )

        root_path = entry[1]
        canonical_path = canonical_entry[1]
        root_size = Path(root_path).stat().st_size
        canonical_size = Path(canonical_path).stat().st_size
        root_hash = _sha256_file(root_path)
        if root_size != canonical_size or root_hash != _sha256_file(canonical_path):
            raise RuntimeError(
                f"Root and canonical Flet binaries differ; refusing removal: {root_name}"
            )

        removed_destinations.add(root_name.casefold())
        removed.append(
            RemovedBinary(
                root_name=root_name,
                canonical_name=canonical_name,
                size_bytes=root_size,
                sha256=root_hash,
            )
        )

    filtered = [
        entry
        for entry in entries
        if _normalise_destination(entry[0]).casefold() not in removed_destinations
    ]
    return filtered, tuple(sorted(removed, key=lambda item: item.root_name.casefold()))
