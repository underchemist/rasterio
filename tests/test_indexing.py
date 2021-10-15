"""Test windows and indexing"""

# TODO: break up multi-assertion tests.

import numpy as np
import pytest

import rasterio
from rasterio.errors import WindowError
from rasterio import windows


DATA_WINDOW = ((3, 5), (2, 6))


def assert_window_almost_equals(a, b, precision=3):
    for attr in ('row_off', 'col_off', 'width', 'height'):
        assert round(getattr(a, attr), precision) == round(getattr(b, attr), precision)


def test_index():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        assert src.index(left, top) == (0, 0)
        assert src.index(right, top) == (0, src.width)
        assert src.index(right, bottom) == (src.height, src.width)
        assert src.index(left, bottom) == (src.height, 0)


def test_full_window():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        assert_window_almost_equals(
            src.window(left, bottom, right, top),
            windows.Window(0, 0, src.width, src.height))


def test_window_no_exception():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        left -= 1000.0
        assert_window_almost_equals(
            src.window(left, bottom, right, top),
            windows.Window(-1000 / src.res[0], 0, src.width + 1000 / src.res[0], src.height))


def test_index_values():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.index(101985.0, 2826915.0) == (0, 0)
        assert src.index(101985.0 + 400.0, 2826915.0) == (0, 1)
        assert src.index(101985.0 + 400.0, 2826915.0 - 700.0) == (2, 1)


def test_window():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res
        eps = 1.0e-8
        assert_window_almost_equals(src.window(
            left + eps, bottom + eps, right - eps, top - eps),
            windows.Window(0, 0, src.width, src.height))
        assert src.index(left + 400, top - 400) == (1, 1)
        assert src.index(left + dx + eps, top - dy - eps) == (1, 1)
        assert_window_almost_equals(src.window(left, top - 400, left + 400, top), windows.Window(0, 0, 400 / src.res[0], 400 / src.res[1]))
        assert_window_almost_equals(src.window(left, top - 2 * dy - eps, left + 2 * dx - eps, top), windows.Window(0, 0, 2, 2))


def test_window_bounds_roundtrip():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert_window_almost_equals(
            windows.Window(100, 100, 100, 100),
            src.window(*src.window_bounds(windows.Window(100, 100, 100, 100))))


def test_window_full_cover():

    def assert_bound_covers(bounds1, bounds2, precision=5):
        """Does bounds1 cover bounds2?
        """
        assert round(bounds1[0], precision) <= round(bounds2[0], precision)
        assert round(bounds1[1], precision) <= round(bounds2[1], precision)
        assert round(bounds1[2], precision) >= round(bounds2[2], precision)
        assert round(bounds1[3], precision) >= round(bounds2[3], precision)

    with rasterio.open('tests/data/RGB.byte.tif') as src:
        bounds = list(src.window_bounds(((100, 200), (100, 200))))
        bounds[1] = bounds[1] - 10.0  # extend south
        bounds[2] = bounds[2] + 10.0  # extend east

        win = src.window(*bounds)
        bounds_calc = list(src.window_bounds(win))
        assert_bound_covers(bounds_calc, bounds)


@pytest.fixture
def data():
    data = np.zeros((10, 10), dtype='uint8')
    data[slice(*DATA_WINDOW[0]), slice(*DATA_WINDOW[1])] = 1
    return data


def test_data_window_unmasked(data):
    window = windows.get_data_window(data)
    assert window == windows.Window.from_slices((0, data.shape[0]), (0, data.shape[1]))


def test_data_window_masked(data):
    data = np.ma.masked_array(data, data == 0)
    window = windows.get_data_window(data)
    assert window == windows.Window.from_slices(*DATA_WINDOW)


def test_data_window_nodata(data):
    window = windows.get_data_window(data, nodata=0)
    assert window == windows.Window.from_slices(*DATA_WINDOW)

    window = windows.get_data_window(np.ones_like(data), nodata=0)
    assert window == windows.Window.from_slices((0, data.shape[0]), (0, data.shape[1]))


def test_data_window_nodata_disjunct():
    data = np.zeros((3, 10, 10), dtype='uint8')
    data[0, :4, 1:4] = 1
    data[1, 2:5, 2:8] = 1
    data[2, 1:6, 1:6] = 1
    window = windows.get_data_window(data, nodata=0)
    assert window == windows.Window.from_slices((0, 6), (1, 8))


def test_data_window_empty_result():
    data = np.zeros((3, 10, 10), dtype='uint8')
    window = windows.get_data_window(data, nodata=0)
    assert window == windows.Window.from_slices((0, 0), (0, 0))


def test_data_window_masked_file():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        window = windows.get_data_window(src.read(1, masked=True))
        assert window == windows.Window.from_slices((3, 714), (13, 770))

        window = windows.get_data_window(src.read(masked=True))
        assert window == windows.Window.from_slices((3, 714), (13, 770))


def test_window_union():
    assert windows.union(
        windows.Window(0, 3, 3, 6),
        windows.Window(2, 1, 2, 4)
    ) == windows.Window(0, 1, 4, 8)


def test_window_intersection():
    assert windows.intersection(
        windows.Window.from_slices((0, 6), (3, 6)),
        windows.Window.from_slices((2, 4), (1, 5))
    ) == windows.Window.from_slices((2, 4), (3, 5))

    assert windows.intersection(
        windows.Window.from_slices((0, 6), (3, 6)),
        windows.Window.from_slices((2, 4), (1, 5)),
        windows.Window.from_slices((3, 6), (0, 6))
    ) == windows.Window.from_slices((3, 4), (3, 5))


def test_window_intersection_disjunct():
    with pytest.raises(WindowError):
        windows.intersection(
            windows.Window.from_slices((0, 6), (3, 6)),
            windows.Window.from_slices((100, 200), (0, 12)),
            windows.Window.from_slices((7, 12), (7, 12)))

        # touch, no overlap on edge of open interval
        assert windows.intersection(
            windows.Window.from_slices((0, 6), (3, 6)),
            windows.Window.from_slices((6, 10), (1, 5)))


def test_windows_intersect():
    assert windows.intersect(
        windows.Window.from_slices((0, 6), (3, 6)),
        windows.Window.from_slices((2, 4), (1, 5))) is True

    assert windows.intersect(
        windows.Window.from_slices((0, 6), (3, 6)),
        windows.Window.from_slices((2, 4), (1, 5)),
        windows.Window.from_slices((3, 6), (0, 6))) is True

    assert windows.intersect(
        windows.Window.from_slices((0, 2), (0, 2)),
        windows.Window.from_slices((1, 4), (1, 4))) is True


def test_3x3matrix():
    """For a 3x3 arrangement of 2x2 windows
      a | b | c
      ---------
      d | e | f
      ---------
      g | h | i

      i.e. window e is ((2, 4), (2, 4))

      None of them should intersect or have an intersection
    """
    from itertools import product, combinations

    pairs = ((0, 2), (2, 4), (4, 6))
    arrangement = product(pairs, pairs)
    for wins in combinations(arrangement, 2):
        _wins = [windows.Window.from_slices(*w) for w in wins]
        assert not windows.intersect(_wins)
        with pytest.raises(WindowError):
            windows.intersection(_wins)


def test_windows_intersect_disjunct():
    assert windows.intersect(
        windows.Window.from_slices((0, 6), (3, 6)),
        windows.Window.from_slices((10, 20), (0, 6))) is False

    # polygons touch at point
    assert windows.intersect(
        windows.Window.from_slices((0, 2), (1, 3)),
        windows.Window.from_slices((2, 4), (3, 5))) is False

    # polygons touch at point, rev order
    assert windows.intersect(
        windows.Window.from_slices((2, 4), (3, 5)),
        windows.Window.from_slices((0, 2), (1, 3))) is False

    # polygons touch at line
    assert windows.intersect(
        windows.Window.from_slices((0, 6), (3, 6)),
        windows.Window.from_slices((6, 10), (1, 5))) is False

    assert windows.intersect(
        windows.Window.from_slices((0, 6), (3, 6)),
        windows.Window.from_slices((2, 4), (1, 5)),
        windows.Window.from_slices((5, 6), (0, 6))) is False

    assert windows.intersect(
        windows.Window.from_slices((0, 6), (3, 6)),
        windows.Window.from_slices((2, 4), (1, 3)),
        windows.Window.from_slices((3, 6), (4, 6))) is False


def test_iter_args_winfuncs():
    wins = [
        windows.Window.from_slices((0, 6), (3, 6)),
        windows.Window.from_slices((2, 4), (1, 5))]

    assert windows.intersect(*wins) == windows.intersect(wins)
    assert windows.intersection(*wins) == windows.intersection(wins)
    assert windows.union(*wins) == windows.union(wins)


def test_iter_args():
    from rasterio.windows import iter_args

    @iter_args
    def foo(*args):
        return len(args)

    assert foo([0, 1, 2]) == foo(0, 1, 2) == foo(range(3)) == 3
