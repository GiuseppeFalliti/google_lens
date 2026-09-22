from src.utils.geometry import Rect, union_rects


def test_rect_from_points_normalizes_coordinates():
    rect = Rect.from_points(20, 30, -10, 5)
    assert rect == Rect(-10, 5, 30, 25)


def test_negative_virtual_desktop_coordinates_are_preserved():
    bounds = union_rects(
        [
            Rect(-1920, 0, 1920, 1080),
            Rect(0, 0, 2560, 1440),
        ]
    )
    assert bounds == Rect(-1920, 0, 4480, 1440)


def test_clamp_region_to_bounds():
    rect = Rect(-50, -50, 200, 200)
    assert rect.clamp(Rect(0, 0, 100, 100)) == Rect(0, 0, 100, 100)
