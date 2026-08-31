from scripts.analyze_package import analyze_package, find_exact_flet_duplicates, module_is_present


def test_module_is_present_matches_package_and_submodule() -> None:
    modules = {"mypy", "mypy.api", "google.genai", "PIL\\Image.pyc"}

    assert module_is_present(modules, "mypy")
    assert module_is_present(modules, "PIL")


def test_module_is_present_does_not_match_similar_prefix() -> None:
    modules = {"lxml_html_clean", "click_plugins"}

    assert not module_is_present(modules, "lxml")
    assert not module_is_present(modules, "click")


def test_find_exact_flet_duplicates_matches_identical_root_file() -> None:
    contents = {
        "flutter_windows.dll": b"same-runtime-binary",
        "flet_desktop\\app\\flet\\flutter_windows.dll": b"same-runtime-binary",
    }
    toc = {name: (0, len(content) - 2, len(content), 1, "b") for name, content in contents.items()}

    duplicates = find_exact_flet_duplicates(toc, contents.__getitem__)

    assert len(duplicates) == 1
    assert duplicates[0].root_name == "flutter_windows.dll"
    assert duplicates[0].compressed_size == len(b"same-runtime-binary") - 2


def test_find_exact_flet_duplicates_rejects_different_content() -> None:
    contents = {
        "libEGL.dll": b"root-version",
        "flet_desktop\\app\\flet\\libEGL.dll": b"runtime-version",
    }
    toc = {name: (0, 10, len(content), 1, "b") for name, content in contents.items()}

    assert find_exact_flet_duplicates(toc, contents.__getitem__) == ()


def test_find_exact_flet_duplicates_requires_canonical_file() -> None:
    contents = {"libmpv-2.dll": b"root-only"}
    toc = {"libmpv-2.dll": (0, 8, 9, 1, "b")}

    assert find_exact_flet_duplicates(toc, contents.__getitem__) == ()


def test_analyze_package_rejects_forbidden_duplicate_suffix(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "app.exe"
    executable.write_bytes(b"archive")
    contents = {
        "window_manager_plugin.dll": b"same",
        "flet_desktop\\app\\flet\\window_manager_plugin.dll": b"same",
    }
    toc = {name: (0, len(content), len(content), 1, "b") for name, content in contents.items()}

    class FakeArchive:
        def __init__(self, _path: str) -> None:
            self.toc = toc

        def extract(self, name: str) -> bytes:
            return contents[name]

    monkeypatch.setattr("scripts.analyze_package.CArchiveReader", FakeArchive)

    analysis = analyze_package(
        executable,
        baseline_bytes=100,
        forbidden_modules=(),
        forbidden_root_duplicate_suffixes=("_plugin.dll",),
    )

    assert analysis.present_forbidden_root_duplicates == ("window_manager_plugin.dll",)


def test_analyze_package_reports_missing_required_entry(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "app.exe"
    executable.write_bytes(b"archive")

    class FakeArchive:
        def __init__(self, _path: str) -> None:
            self.toc = {"flet_desktop\\app\\flet\\flet.exe": (0, 1, 1, 1, "b")}

        def extract(self, _name: str) -> bytes:
            return b"x"

    monkeypatch.setattr("scripts.analyze_package.CArchiveReader", FakeArchive)

    analysis = analyze_package(
        executable,
        baseline_bytes=100,
        forbidden_modules=(),
        required_entries=(
            "flet_desktop/app/flet/flet.exe",
            "flet_desktop/app/flet/flutter_windows.dll",
        ),
    )

    assert analysis.missing_required_entries == ("flet_desktop/app/flet/flutter_windows.dll",)
