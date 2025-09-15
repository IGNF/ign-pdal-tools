import math
import os
import shutil

import numpy as np
import pytest
import requests
import requests_mock
from osgeo import gdal

import pdaltools.download_image

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMPDIR = os.path.join(TEST_PATH, "tmp", "download_image")

OUTPUT_FILE = os.path.join(TMPDIR, "download_image.tif")

EPSG = "2154"
LAYER = "ORTHOIMAGERY.ORTHOPHOTOS"
MINX = 435000
MINY = 6291000
MAXX = 436000
MAXY = 6292000
PIXEL_PER_METER = 0.1
SIZE_MAX_IMAGE_GPF = 500


def setup_module(module):
    try:
        shutil.rmtree(TMPDIR)
    except FileNotFoundError:
        pass
    os.mkdir(TMPDIR)


@pytest.mark.parametrize(
    "mind, maxd, pixel_per_meter, size_max_gpf, expected_nb_pixels, expected_nb_cells, expected_cell_size",
    [
        (0, 1000, 1, 500, 1000, 2, 500),  # Easy case, sizes match perfectly
        (0, 1001, 1, 1000, 1001, 2, 501),  # Image slightly bigger than size_max_gpf
        (0.1, 999.2, 1, 500, 1000, 2, 500),  # floating value for min/max
    ],
)
def test_compute_cells_size(
    mind, maxd, pixel_per_meter, size_max_gpf, expected_nb_pixels, expected_nb_cells, expected_cell_size
):
    nb_pixels, nb_cells, cell_size = pdaltools.download_image.compute_cells_size(
        mind, maxd, pixel_per_meter, size_max_gpf
    )
    assert nb_pixels == expected_nb_pixels
    assert nb_cells == expected_nb_cells
    assert cell_size == expected_cell_size


@pytest.mark.geopf
def test_download_image_ok():
    tif_output = os.path.join(TMPDIR, "download_image.tif")
    pdaltools.download_image.download_image(
        EPSG, LAYER, MINX, MINY, MAXX, MAXY, PIXEL_PER_METER, tif_output, 15, True, size_max_gpf=SIZE_MAX_IMAGE_GPF
    )

    # check there is no noData
    raster = gdal.Open(tif_output)
    assert np.any(raster.ReadAsArray())  # Check that the raster array is not empty


@pytest.mark.geopf
def test_download_image_ok_one_download():
    tif_output = os.path.join(TMPDIR, "download_image.tif")
    expected_pixel_size = 100  # (MAXX - MINX) * PIXEL_PER_METER
    nb_request = pdaltools.download_image.download_image(
        EPSG, LAYER, MINX, MINY, MAXX, MAXY, PIXEL_PER_METER, tif_output, 15, True, size_max_gpf=1000
    )
    assert nb_request == 1

    # check there is no noData
    raster = gdal.Open(tif_output)
    assert raster.ReadAsArray().shape == (3, expected_pixel_size, expected_pixel_size)
    assert np.any(raster.ReadAsArray())  # Check that the raster array is not empty

    # TODO: Fix this test: it did not correspond to what was expected:
    # - GetNoDataValue returns the value of no_data, not the number of occurrences
    # - it is possible to have occasional no data values if no_data == 255. (white pixels)
    # for i in range(raster.RasterCount):
    #     assert raster.GetRasterBand(i + 1).GetNoDataValue() is None


@pytest.mark.geopf
@pytest.mark.parametrize("pixel_per_meter, expected_pixel_size", [(0.5, 501), (1, 1001), (2, 2001)])
def test_download_image_ok_one_download_with_extra_pixel(pixel_per_meter, expected_pixel_size):
    # test with 1 extra pixel to compensate the phase difference between raster and lidar
    tif_output = os.path.join(TMPDIR, "download_image.tif")

    maxx = MAXX + 1 / pixel_per_meter
    maxy = MAXY + 1 / pixel_per_meter
    nb_request = pdaltools.download_image.download_image(
        EPSG, LAYER, MINX, MINY, maxx, maxy, pixel_per_meter, tif_output, 15, True, size_max_gpf=5000
    )
    assert nb_request == 1

    # check there is no noData
    raster = gdal.Open(tif_output)

    assert raster.ReadAsArray().shape == (3, expected_pixel_size, expected_pixel_size)
    assert np.any(raster.ReadAsArray())  # Check that the raster array is not empty

    # TODO: Fix this test: it did not correspond to what was expected:
    # - GetNoDataValue returns the value of no_data, not the number of occurrences
    # - it is possible to have occasional no data values if no_data == 255. (white pixels)
    # for i in range(raster.RasterCount):
    #     assert raster.GetRasterBand(i + 1).GetNoDataValue() is None


@pytest.mark.geopf
@pytest.mark.parametrize("pixel_per_meter, expected_pixel_size", [(0.5, 500), (1, 1000), (2, 2000), (5, 5000)])
def test_download_image_ok_more_downloads(pixel_per_meter, expected_pixel_size):
    tif_output = os.path.join(TMPDIR, f"download_image_resolution_{pixel_per_meter}.tif")

    nb_request = pdaltools.download_image.download_image(
        EPSG,
        LAYER,
        MINX,
        MINY,
        MAXX,
        MAXY,
        pixel_per_meter,
        tif_output,
        15,
        True,
        size_max_gpf=1000,
    )
    assert nb_request == max(1, 1 * pixel_per_meter * pixel_per_meter)

    # check there is no noData
    raster = gdal.Open(tif_output)
    assert raster.ReadAsArray().shape == (3, expected_pixel_size, expected_pixel_size)
    assert np.any(raster.ReadAsArray())  # Check that the raster array is not empty

    # TODO: Fix this test: it did not correspond to what was expected:
    # - GetNoDataValue returns the value of no_data, not the number of occurrences
    # - it is possible to have occasional no data values if no_data == 255. (white pixels)
    # for i in range(raster.RasterCount):
    #     assert raster.GetRasterBand(i + 1).GetNoDataValue() is None


@pytest.mark.geopf
@pytest.mark.parametrize(
    "pixel_per_meter, expected_nb_requests, expected_pixel_size",
    [(0.5, 1, 501), (1, 4, 1001), (2, 9, 2001), (4, 25, 4001)],
)
def test_download_image_ok_more_downloads_with_extra_pixel(pixel_per_meter, expected_nb_requests, expected_pixel_size):
    # test with 1 extra pixel to compensate the phase difference between raster and lidar
    tif_output = os.path.join(TMPDIR, "download_image.tif")
    maxx = MAXX + 1 / pixel_per_meter
    maxy = MAXY + 1 / pixel_per_meter
    nb_request = pdaltools.download_image.download_image(
        EPSG, LAYER, MINX, MINY, maxx, maxy, pixel_per_meter, tif_output, 15, True, size_max_gpf=1000
    )
    assert nb_request == expected_nb_requests

    # check there is no noData
    raster = gdal.Open(tif_output)
    assert raster.ReadAsArray().shape == (3, expected_pixel_size, expected_pixel_size)
    assert np.any(raster.ReadAsArray())  # Check that the raster array is not empty

    # TODO: Fix this test: it did not correspond to what was expected:
    # - GetNoDataValue returns the value of no_data, not the number of occurrences
    # - it is possible to have occasional no data values if no_data == 255. (white pixels)
    # for i in range(raster.RasterCount):
    #     assert raster.GetRasterBand(i + 1).GetNoDataValue() is None


@pytest.mark.geopf
def test_download_image_download_size_gpf_bigger():
    tif_output = os.path.join(TMPDIR, "download_image_bigger.tif")
    pdaltools.download_image.download_image(
        EPSG, LAYER, MINX, MINY, MAXX, MAXY, PIXEL_PER_METER, tif_output, 15, True, size_max_gpf=1005
    )

    # check there is no noData
    raster = gdal.Open(tif_output)
    assert np.any(raster.ReadAsArray())  # Check that the raster array is not empty

    # TODO: Fix this test: it did not correspond to what was expected:
    # - GetNoDataValue returns the value of no_data, not the number of occurrences
    # - it is possible to have occasional no data values if no_data == 255. (white pixels)
    # for i in range(raster.RasterCount):
    #     assert raster.GetRasterBand(i + 1).GetNoDataValue() is None


@pytest.mark.geopf
def test_download_image_download_size_gpf_size_almost_ok():
    tif_output = os.path.join(TMPDIR, "download_image_bigger.tif")
    nb_request = pdaltools.download_image.download_image(
        EPSG, LAYER, MINX, MINY, MAXX, MAXY, PIXEL_PER_METER, tif_output, 15, True, size_max_gpf=99
    )
    assert nb_request == 4

    # check there is no noData
    raster = gdal.Open(tif_output)
    assert np.any(raster.ReadAsArray())  # Check that the raster array is not empty


@pytest.mark.geopf
@pytest.mark.parametrize("size_block", [100, 50, 25])
def test_download_image_compare_one_and_block(size_block):
    tif_output_one = os.path.join(TMPDIR, "download_image_one.tif")
    nb_request = pdaltools.download_image.download_image(
        EPSG, LAYER, MINX, MINY, MAXX, MAXY, PIXEL_PER_METER, tif_output_one, 15, True, 100
    )
    assert nb_request == 1

    tif_output_blocks = os.path.join(TMPDIR, "download_image_block.tif")
    nb_request = pdaltools.download_image.download_image(
        EPSG, LAYER, MINX, MINY, MAXX, MAXY, PIXEL_PER_METER, tif_output_blocks, 100, True, size_block
    )
    assert nb_request == math.pow(1000 * PIXEL_PER_METER / size_block, 2)

    # due to GeoPlateforme interpolation, images could have small differences
    # check images are almost the same

    raster_one = gdal.Open(tif_output_one)
    raster_blocks = gdal.Open(tif_output_blocks)

    r_one = np.array(raster_one.ReadAsArray())
    r_blocks = np.array(raster_blocks.ReadAsArray())
    assert r_one.size == r_blocks.size
    r_diff = r_one - r_blocks

    # images should be same as 5/1000 (tolerance)
    assert np.count_nonzero(r_diff) < 0.005 * ((MAXX - MINX) * (MAXY - MINY) * math.pow(PIXEL_PER_METER, 2))

    # differences should be 1 or 255 (eq a variation of one on one RVB canal)
    r_diff_nonzero = np.nonzero(r_diff)
    for i in range(0, r_diff_nonzero[0].size):
        diff = r_diff[r_diff_nonzero[0][i], r_diff_nonzero[1][i], r_diff_nonzero[2][i]]
        assert diff == 1 or diff == 255


def test_is_image_white_true():
    input_path = os.path.join(TEST_PATH, "data/image/white.tif")
    assert pdaltools.download_image.is_image_white(input_path), "This image should be detected as white"


def test_is_image_white_false():
    input_path = os.path.join(TEST_PATH, "data/image/colored.tif")
    assert not pdaltools.download_image.is_image_white(input_path), "This image should NOT be detected as white"


@pytest.mark.geopf
def test_download_image_raise1():
    retry_download = pdaltools.download_image.retry(times=2, delay=5, factor=2)(
        pdaltools.download_image.download_image_from_geoplateforme
    )
    with pytest.raises(requests.exceptions.HTTPError):
        retry_download(EPSG, "MAUVAISE_COUCHE", MINX, MINY, MAXX, MAXY, 100, 100, OUTPUT_FILE, 15, True)


@pytest.mark.geopf
def test_download_image_raise2():
    retry_download = pdaltools.download_image.retry(times=2, delay=5, factor=2)(
        pdaltools.download_image.download_image_from_geoplateforme
    )
    with pytest.raises(requests.exceptions.HTTPError):
        retry_download("9001", LAYER, MINX, MINY, MAXX, MAXY, 100, 100, OUTPUT_FILE, 15, True)


def test_retry_on_server_error():
    with requests_mock.Mocker() as mock:
        mock.get(requests_mock.ANY, status_code=502, reason="Bad Gateway")
        with pytest.raises(requests.exceptions.HTTPError):
            retry_download = pdaltools.download_image.retry(times=2, delay=1, factor=2)(
                pdaltools.download_image.download_image_from_geoplateforme
            )
            retry_download(EPSG, LAYER, MINX, MINY, MAXX, MAXY, 100, 100, OUTPUT_FILE, 15, True)
        history = mock.request_history
        assert len(history) == 3


def test_retry_on_connection_error():
    with requests_mock.Mocker() as mock:
        mock.get(requests_mock.ANY, exc=requests.exceptions.ConnectionError)
        with pytest.raises(requests.exceptions.ConnectionError):
            retry_download = pdaltools.download_image.retry(times=2, delay=1, factor=2)(
                pdaltools.download_image.download_image_from_geoplateforme
            )
            retry_download(EPSG, LAYER, MINX, MINY, MAXX, MAXY, 100, 100, OUTPUT_FILE, 15, True)

        history = mock.request_history
        assert len(history) == 3


def test_retry_param():
    # Here you can change retry params
    @pdaltools.download_image.retry(times=9, delay=5, factor=2, debug=True)
    def raise_server_error():
        raise requests.exceptions.HTTPError("Server Error")

    with pytest.raises(requests.exceptions.HTTPError):
        raise_server_error()
