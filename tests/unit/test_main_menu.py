from typing import Any, cast

from main import close_app


class FakeWindow:
    def __init__(self) -> None:
        self.close_count = 0

    def close(self) -> None:
        self.close_count += 1


class FakePage:
    def __init__(self) -> None:
        self.window = FakeWindow()


def test_close_app_closes_window_once() -> None:
    page = FakePage()

    close_app(cast(Any, page))

    assert page.window.close_count == 1
