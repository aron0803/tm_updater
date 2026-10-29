"""
Contract tests for window placement (spec: gui_folder_dialog_spec.md section 3.1).

The field bug: a portrait 1080x1920 panel at 125% scaling makes WinForms report
Screen.Bounds = 1920x1080 / scale 1.0, so a 1200 px window centered on that phantom
canvas opens 853 px past the right edge.  fit_and_center must work from the real
work area instead.
"""

from __future__ import annotations

from updater.gui.placement import (
    WorkArea,
    apply_window_rect,
    center_on_monitor,
    find_window,
    fit_and_center,
    monitor_work_area,
)

LANDSCAPE = WorkArea(0, 0, 1920, 1020)
# same panel rotated: narrower than the default window
PORTRAIT = WorkArea(0, 0, 1080, 1912)


class TestFitAndCenter:
    def test_centers_when_it_fits(self) -> None:
        x, y, w, h = fit_and_center(LANDSCAPE, 1200, 756)
        assert (w, h) == (1200, 756)
        assert (x, y) == (360, 132)

    def test_shrinks_when_the_screen_is_narrower_than_the_window(self) -> None:
        x, y, w, h = fit_and_center(PORTRAIT, 1200, 756)
        assert w == 1072, "the window must never be wider than the monitor"
        assert h == 756
        assert 0 <= x and x + w <= PORTRAIT.width

    def test_stays_inside_the_work_area_in_every_case(self) -> None:
        for work in (
            LANDSCAPE,
            PORTRAIT,
            WorkArea(1920, 0, 1280, 1024),  # second monitor, offset origin
            WorkArea(0, 0, 640, 480),  # smaller than MIN_WINDOW_SIZE
        ):
            x, y, w, h = fit_and_center(work, 1200, 1000)
            assert w <= work.width and h <= work.height
            assert x >= work.x and y >= work.y
            assert x + w <= work.x + work.width
            assert y + h <= work.y + work.height

    def test_the_requested_size_is_converted_by_the_monitor_dpi(self) -> None:
        # measured field display: 1920x1080 work area at 124% scaling
        work = WorkArea(0, 0, 1920, 1020, scale=119 / 96)
        x, y, w, h = fit_and_center(work, 1200, 756)
        assert (w, h) == (1488, 937), "1200 logical px must become 1488 device px"
        assert x == 216 and y == 41
        assert x + w <= 1920 and y + h <= 1020, "and still fit inside the work area"

    def test_a_scaled_window_bigger_than_the_screen_is_clamped(self) -> None:
        work = WorkArea(0, 0, 1366, 768, scale=1.5)  # 1200*1.5 = 1800 > 1366
        x, y, w, h = fit_and_center(work, 1200, 500)
        assert w == 1358 and x + w <= 1366

    def test_the_second_monitor_origin_is_respected(self) -> None:
        work = WorkArea(1920, 0, 1280, 1024)
        x, y, w, h = fit_and_center(work, 1000, 700)
        assert x == 1920 + 140 and y == 162

    def test_a_degenerate_work_area_still_returns_usable_numbers(self) -> None:
        x, y, w, h = fit_and_center(WorkArea(0, 0, 1, 1), 1200, 700)
        assert (w, h) == (1, 1)
        assert (x, y) == (0, 0)


class TestWin32:
    def test_unknown_title_is_reported_not_raised(self) -> None:
        assert find_window("tm_updater-no-such-window") == 0
        assert monitor_work_area(0) is None
        note = center_on_monitor("tm_updater-no-such-window", 1200, 700)
        assert "找不到視窗" in note

    def test_a_bad_handle_does_not_raise(self) -> None:
        assert apply_window_rect(0, 10, 10, 100, 100) is False
