"""Inspect a PyInstaller executable and enforce release size/module gates."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

DEFAULT_BASELINE_BYTES = 102_664_931


@dataclass(frozen=True)
class PackageAnalysis:
    path: str
    size_bytes: int
    baseline_bytes: int
    reduction_bytes: int
    reduction_percent: float
    present_forbidden_modules: tuple[str, ...]


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
) -> PackageAnalysis:
    if not executable.is_file():
        raise FileNotFoundError(f"Executable was not found: {executable}")

    size_bytes = executable.stat().st_size
    reduction_bytes = baseline_bytes - size_bytes
    reduction_percent = reduction_bytes / baseline_bytes * 100
    module_names = archive_module_names(executable)
    present = tuple(
        module for module in forbidden_modules if module_is_present(module_names, module)
    )
    return PackageAnalysis(
        path=str(executable.resolve()),
        size_bytes=size_bytes,
        baseline_bytes=baseline_bytes,
        reduction_bytes=reduction_bytes,
        reduction_percent=reduction_percent,
        present_forbidden_modules=present,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--baseline", type=int, default=DEFAULT_BASELINE_BYTES)
    parser.add_argument("--maximum", type=int)
    parser.add_argument("--forbid", action="append", default=[])
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    analysis = analyze_package(
        args.executable,
        baseline_bytes=args.baseline,
        forbidden_modules=args.forbid,
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

    if args.json_output:
        args.json_output.write_text(
            json.dumps(asdict(analysis), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    failed = bool(analysis.present_forbidden_modules)
    if args.maximum is not None and analysis.size_bytes > args.maximum:
        print(f"Size gate failed: maximum is {args.maximum:,} bytes")
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
