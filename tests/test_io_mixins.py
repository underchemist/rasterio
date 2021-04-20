from affine import Affine
import pytest

import rasterio
from rasterio.errors import RasterioDeprecationWarning
from rasterio.windows import Window, WindowMethodsMixin


EPS = 1.0e-8


def assert_window_almost_equals(a, b, precision=3):
    assert round(a.col_off, precision) == round(b.col_off, precision)
    assert round(a.row_off, precision) == round(b.row_off, precision)
    assert round(a.width, precision) == round(b.width, precision)
    assert round(a.height, precision) == round(b.height, precision)


class MockDatasetBase:
    def __init__(self):
        # from tests/data/RGB.byte.tif
        self.affine = Affine(300.0379266750948, 0.0, 101985.0,
                             0.0, -300.041782729805, 2826915.0)
        self.bounds = (101985.0, 2611485.0, 339315.0, 2826915.0)
        self.transform = self.affine
        self.height = 718
        self.width = 791


def test_windows_mixin():

    class MockDataset(MockDatasetBase, WindowMethodsMixin):
        pass

    src = MockDataset()

    assert_window_almost_equals(
        src.window(*src.bounds),
        Window(0, 0, src.width, src.height)
    )

    assert src.window_bounds(Window(0, 0, src.width, src.height)) == src.bounds

    assert src.window_transform(
        Window(0, 0, src.width, src.height)) == src.transform


def test_windows_mixin_fail():

    class MockDataset(WindowMethodsMixin):
        # doesn't inherit transform, height and width
        pass

    src = MockDataset()
    with pytest.raises(TypeError):
        src.window()
    with pytest.raises(TypeError):
        src.window_bounds()
    with pytest.raises(TypeError):
        src.window_transform()


def test_window_transform_method():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.window_transform(Window(0, 0, None, None)) == src.transform
        assert src.window_transform(Window(None, None, None, None)) == src.transform
        assert src.window_transform(
            Window(1, 1, None, None)).c == src.bounds.left + src.res[0]
        assert src.window_transform(
            ((1, None), (1, None))).f == src.bounds.top - src.res[1]
        assert src.window_transform(
            ((-1, None), (-1, None))).c == src.bounds.left - src.res[0]
        assert src.window_transform(
            ((-1, None), (-1, None))).f == src.bounds.top + src.res[1]


def test_window_method():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res

        assert_window_almost_equals(
            src.window(left + EPS, bottom + EPS, right - EPS, top - EPS),
            Window(0, 0, src.width, src.height)
            )

        assert_window_almost_equals(
            src.window(left, top - 400, left + 400, top),
                       Window(0, 0, 400 / src.res[0], 400 / src.res[1])
            )

        assert_window_almost_equals(
            src.window(left, top - 2 * dy - EPS, left + 2 * dx - EPS, top),
            Window(0, 0, 2, 2))

        assert_window_almost_equals(
            src.window(left - 2 * dx, top - 2 * dy, left + 2 * dx, top + 2 * dy),
            Window(-2, -2, 4, 4)
        )


def test_window_bounds_function():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        rows = src.height
        cols = src.width
        assert src.window_bounds(((0, rows), (0, cols))) == src.bounds
