"""Inspect a PyInstaller executable and enforce release size/module gates."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PyInstaller.archive.readers import CArchiveReader

DEFAULT_BASELINE_BYTES = 102_664_931
FLET_RUNTIME_PREFIX = "flet_desktop\\app\\flet\\"


@dataclass(frozen=True)
class ExactDuplicate:
    root_name: str
    canonical_name: str
    compressed_size: int
    uncompressed_size: int
    sha256: str


@dataclass(frozen=True)
class PackageAnalysis:
    path: str
    size_bytes: int
    baseline_bytes: int
    reduction_bytes: int
    reduction_percent: float
    present_forbidden_modules: tuple[str, ...]
    exact_flet_duplicates: tuple[ExactDuplicate, ...]
    duplicate_compressed_bytes: int
    present_forbidden_root_duplicates: tuple[str, ...]
    missing_required_entries: tuple[str, ...]


def _normalise_module_name(name: str) -> str:
    return name.replace("\\", ".").replace("/", ".").removesuffix(".pyc")


def module_is_present(module_names: Iterable[str], package_name: str) -> bool:
    """Return whether an exact package or one of its descendants is present."""
    package_name = _normalise_module_name(package_name)
    return any(
        (normalised := _normalise_module_name(name)) == package_name
        or normalised.startswith(f"{package_name}.")
        for name in module_names
    )


def find_exact_flet_duplicates(
    toc: Mapping[str, tuple[Any, ...]],
    extract: Callable[[str], bytes],
) -> tuple[ExactDuplicate, ...]:
    """Find byte-identical root/Flet-runtime file pairs in a CArchive."""
    duplicates: list[ExactDuplicate] = []
    for root_name, root_entry in toc.items():
        if "\\" in root_name or "/" in root_name:
            continue
        canonical_name = f"{FLET_RUNTIME_PREFIX}{root_name}"
        canonical_entry = toc.get(canonical_name)
        if canonical_entry is None or root_entry[2] != canonical_entry[2]:
            continue

        root_bytes = extract(root_name)
        canonical_bytes = extract(canonical_name)
        if root_bytes != canonical_bytes:
            continue
        duplicates.append(
            ExactDuplicate(
                root_name=root_name,
                canonical_name=canonical_name,
                compressed_size=int(root_entry[1]),
                uncompressed_size=int(root_entry[2]),
                sha256=hashlib.sha256(root_bytes).hexdigest(),
            )
        )
    return tuple(sorted(duplicates, key=lambda item: item.root_name.casefold()))


def archive_module_names(executable: Path) -> set[str]:
    """Return names from the outer CArchive and its embedded PYZ archive."""
    archive = CArchiveReader(str(executable))
    names = set(archive.toc)
    if "PYZ.pyz" in archive.toc:
        pyz_archive = archive.open_embedded_archive("PYZ.pyz")
        names.update(pyz_archive.toc)
    return names


def analyze_package(
    executable: Path,
    *,
    baseline_bytes: int,
    forbidden_modules: Iterable[str],
    forbidden_root_duplicates: Iterable[str] = (),
    forbidden_root_duplicate_suffixes: Iterable[str] = (),
    required_entries: Iterable[str] = (),
) -> PackageAnalysis:
    if not executable.is_file():
        raise FileNotFoundError(f"Executable was not found: {executable}")

    size_bytes = executable.stat().st_size
    reduction_bytes = baseline_bytes - size_bytes
    reduction_percent = reduction_bytes / baseline_bytes * 100
    archive = CArchiveReader(str(executable))
    module_names = set(archive.toc)
    if "PYZ.pyz" in archive.toc:
        module_names.update(archive.open_embedded_archive("PYZ.pyz").toc)
    present = tuple(
        module for module in forbidden_modules if module_is_present(module_names, module)
    )
    duplicates = find_exact_flet_duplicates(archive.toc, archive.extract)
    duplicate_names = {duplicate.root_name.casefold() for duplicate in duplicates}
    present_forbidden_duplicates = list(
        name for name in forbidden_root_duplicates if name.casefold() in duplicate_names
    )
    suffixes = tuple(suffix.casefold() for suffix in forbidden_root_duplicate_suffixes)
    present_forbidden_duplicates.extend(
        duplicate.root_name
        for duplicate in duplicates
        if suffixes and duplicate.root_name.casefold().endswith(suffixes)
    )
    archive_names = {name.replace("/", "\\").casefold() for name in archive.toc}
    missing_required_entries = tuple(
        name for name in required_entries if name.replace("/", "\\").casefold() not in archive_names
    )
    return PackageAnalysis(
        path=str(executable.resolve()),
        size_bytes=size_bytes,
        baseline_bytes=baseline_bytes,
        reduction_bytes=reduction_bytes,
        reduction_percent=reduction_percent,
        present_forbidden_modules=present,
        exact_flet_duplicates=duplicates,
        duplicate_compressed_bytes=sum(item.compressed_size for item in duplicates),
        present_forbidden_root_duplicates=tuple(dict.fromkeys(present_forbidden_duplicates)),
        missing_required_entries=missing_required_entries,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--baseline", type=int, default=DEFAULT_BASELINE_BYTES)
    parser.add_argument("--maximum", type=int)
    parser.add_argument("--forbid", action="append", default=[])
    parser.add_argument("--forbid-root-duplicate", action="append", default=[])
    parser.add_argument("--forbid-root-duplicate-suffix", action="append", default=[])
    parser.add_argument("--maximum-duplicate-bytes", type=int)
    parser.add_argument("--require-entry", action="append", default=[])
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    analysis = analyze_package(
        args.executable,
        baseline_bytes=args.baseline,
        forbidden_modules=args.forbid,
        forbidden_root_duplicates=args.forbid_root_duplicate,
        forbidden_root_duplicate_suffixes=args.forbid_root_duplicate_suffix,
        required_entries=args.require_entry,
    )

    print(f"Executable: {analysis.path}")
    print(f"Size: {analysis.size_bytes:,} bytes")
    print(
        "Reduction from baseline: "
        f"{analysis.reduction_bytes:,} bytes ({analysis.reduction_percent:.2f}%)"
    )
    if args.forbid:
        if analysis.present_forbidden_modules:
            print("Forbidden modules present: " + ", ".join(analysis.present_forbidden_modules))
        else:
            print("Forbidden modules present: none")
    print(
        "Exact root/Flet-runtime duplicates: "
        f"{len(analysis.exact_flet_duplicates)} files, "
        f"{analysis.duplicate_compressed_bytes:,} compressed bytes"
    )
    if args.forbid_root_duplicate or args.forbid_root_duplicate_suffix:
        if analysis.present_forbidden_root_duplicates:
            print(
                "Forbidden root duplicates present: "
                + ", ".join(analysis.present_forbidden_root_duplicates)
            )
        else:
            print("Forbidden root duplicates present: none")
    if args.require_entry:
        if analysis.missing_required_entries:
            print(
                "Required archive entries missing: " + ", ".join(analysis.missing_required_entries)
            )
        else:
            print("Required archive entries missing: none")

    if args.json_output:
        args.json_output.write_text(
            json.dumps(asdict(analysis), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    failed = bool(
        analysis.present_forbidden_modules
        or analysis.present_forbidden_root_duplicates
        or analysis.missing_required_entries
    )
    if args.maximum is not None and analysis.size_bytes > args.maximum:
        print(f"Size gate failed: maximum is {args.maximum:,} bytes")
        failed = True
    if (
        args.maximum_duplicate_bytes is not None
        and analysis.duplicate_compressed_bytes > args.maximum_duplicate_bytes
    ):
        print(
            "Duplicate-size gate failed: maximum is "
            f"{args.maximum_duplicate_bytes:,} compressed bytes"
        )
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
