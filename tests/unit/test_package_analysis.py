from scripts.analyze_package import module_is_present


def test_module_is_present_matches_package_and_submodule() -> None:
    modules = {"mypy", "mypy.api", "google.genai", "PIL\\Image.pyc"}

    assert module_is_present(modules, "mypy")
    assert module_is_present(modules, "PIL")


def test_module_is_present_does_not_match_similar_prefix() -> None:
    modules = {"lxml_html_clean", "click_plugins"}

    assert not module_is_present(modules, "lxml")
    assert not module_is_present(modules, "click")
