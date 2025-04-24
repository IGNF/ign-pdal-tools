import math
import os
import shutil
from pathlib import Path

import laspy
import numpy as np
import pytest
import requests
import requests_mock
from osgeo import gdal

from pdaltools import color

cwd = os.getcwd()

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMPDIR = os.path.join(TEST_PATH, "tmp")

INPUT_PATH = os.path.join(TEST_PATH, "data/test_noepsg_043500_629205_IGN69.laz")

OUTPUT_FILE = os.path.join(TMPDIR, "Semis_2021_0435_6292_LA93_IGN69.colorized.las")
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


@pytest.mark.geopf
def test_epsg_fail():
    with pytest.raises(
        RuntimeError,
        match="EPSG could not be inferred from metadata: No 'srs' key in metadata.",
    ):
        color.color(INPUT_PATH, OUTPUT_FILE, "", 0.1, 15)


@pytest.mark.geopf
def test_color_and_keeping_orthoimages():
    tmp_ortho, tmp_ortho_irc = color.color(INPUT_PATH, OUTPUT_FILE, EPSG, check_images=True)
    assert Path(tmp_ortho.name).exists()
    assert Path(tmp_ortho_irc.name).exists()


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
    nb_pixels, nb_cells, cell_size = color.compute_cells_size(mind, maxd, pixel_per_meter, size_max_gpf)
    assert nb_pixels == expected_nb_pixels
    assert nb_cells == expected_nb_cells
    assert cell_size == expected_cell_size


@pytest.mark.geopf
def test_download_image_ok():
    tif_output = os.path.join(TMPDIR, "download_image.tif")
    color.download_image(
        EPSG, LAYER, MINX, MINY, MAXX, MAXY, PIXEL_PER_METER, tif_output, 15, True, size_max_gpf=SIZE_MAX_IMAGE_GPF
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
def test_download_image_ok_one_download():
    tif_output = os.path.join(TMPDIR, "download_image.tif")
    expected_pixel_size = 100  # (MAXX - MINX) * PIXEL_PER_METER
    nb_request = color.download_image(
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
    nb_request = color.download_image(
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

    nb_request = color.download_image(
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
    nb_request = color.download_image(
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
    color.download_image(EPSG, LAYER, MINX, MINY, MAXX, MAXY, PIXEL_PER_METER, tif_output, 15, True, size_max_gpf=1005)

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
    nb_request = color.download_image(
        EPSG, LAYER, MINX, MINY, MAXX, MAXY, PIXEL_PER_METER, tif_output, 15, True, size_max_gpf=99
    )
    assert nb_request == 4

    # check there is no noData
    raster = gdal.Open(tif_output)
    assert np.any(raster.ReadAsArray())  # Check that the raster array is not empty
    # TODO: Fix this test: it did not correspond to what was expected:
    # - GetNoDataValue returns the value of no_data, not the number of occurrences
    # - it is possible to have occasional no data values if no_data == 255. (white pixels)
    # for i in range(raster.RasterCount):
    #     assert raster.GetRasterBand(i + 1).GetNoDataValue() is None


@pytest.mark.geopf
@pytest.mark.parametrize("size_block", [100, 50, 25])
def test_download_image_compare_one_and_block(size_block):
    tif_output_one = os.path.join(TMPDIR, "download_image_one.tif")
    nb_request = color.download_image(
        EPSG, LAYER, MINX, MINY, MAXX, MAXY, PIXEL_PER_METER, tif_output_one, 15, True, 100
    )
    assert nb_request == 1

    tif_output_blocks = os.path.join(TMPDIR, "download_image_block.tif")
    nb_request = color.download_image(
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


@pytest.mark.parametrize(
    "minx, maxx, pixel_per_meter, expected_minx, expected_maxx",
    [(500, 1000, 5, 499.8, 1000.2), [1.1, 999.9, 5, 1, 1000]],
)
def test_match_min_max_with_pixel_size(minx, maxx, pixel_per_meter, expected_minx, expected_maxx):
    out_minx, out_maxx = color.match_min_max_with_pixel_size(minx, maxx, pixel_per_meter)
    assert (out_minx, out_maxx) == (expected_minx, expected_maxx)


@pytest.mark.geopf
def test_color_narrow_cloud():
    input_path = os.path.join(TEST_PATH, "data/test_data_0436_6384_LA93_IGN69_single_point.laz")
    output_path = os.path.join(TMPDIR, "color_narrow_cloud_test_data_0436_6384_LA93_IGN69_single_point.colorized.laz")
    # Test that clouds that are smaller in width or height to 20cm are still colorized without an error.
    color.color(input_path, output_path, EPSG)
    with laspy.open(output_path, "r") as las:
        las_data = las.read()
    # Check all points are colored
    assert not np.any(las_data.red == 0)
    assert not np.any(las_data.green == 0)
    assert not np.any(las_data.blue == 0)
    assert not np.any(las_data.nir == 0)


@pytest.mark.geopf
def test_color_standard_cloud():
    input_path = os.path.join(TEST_PATH, "data/test_data_77055_627760_LA93_IGN69.laz")
    output_path = os.path.join(TMPDIR, "color_standard_cloud_test_data_77055_627760_LA93_IGN69.colorized.laz")
    # Test that clouds that are smaller in width or height to 20cm are still colorized without an error.
    color.color(input_path, output_path, EPSG)
    with laspy.open(output_path, "r") as las:
        las_data = las.read()
    # Check all points are colored
    las_rgb_missing = (las_data.red == 0) & (las_data.green == 0) & (las_data.blue == 0)
    assert not np.any(las_rgb_missing), f"Should be no missing RGB value, got {np.count_nonzero(las_rgb_missing)} "
    assert not np.any(las_data.nir == 0)


@pytest.mark.geopf
def test_color_epsg_2975_forced():
    input_path = os.path.join(TEST_PATH, "data/sample_lareunion_epsg2975.laz")
    output_path = os.path.join(TMPDIR, "color_epsg_2975_forced_sample_lareunion_epsg2975.colorized.laz")

    color.color(input_path, output_path, 2975)


def test_is_image_white_true():
    input_path = os.path.join(TEST_PATH, "data/image/white.tif")
    assert color.is_image_white(input_path), "This image should be detected as white"


def test_is_image_white_false():
    input_path = os.path.join(TEST_PATH, "data/image/colored.tif")
    assert not color.is_image_white(input_path), "This image should NOT be detected as white"


@pytest.mark.geopf
def test_color_raise_for_white_image():
    input_path = os.path.join(TEST_PATH, "data/sample_lareunion_epsg2975.laz")
    output_path = os.path.join(TMPDIR, "sample_lareunion_epsg2975.colorized.white.laz")

    with pytest.raises(ValueError) as excinfo:
        color.color(input_path, output_path, check_images=True)

    assert "Downloaded image is white" in str(excinfo.value)


@pytest.mark.geopf
def test_color_epsg_2975_detected():
    input_path = os.path.join(TEST_PATH, "data/sample_lareunion_epsg2975.laz")
    output_path = os.path.join(TMPDIR, "color_epsg_2975_detected_sample_lareunion_epsg2975.colorized.laz")
    # Test that clouds that are smaller in width or height to 20cm are still clorized without an error.
    color.color(input_path, output_path)


@pytest.mark.geopf
def test_download_image_raise1():
    retry_download = color.retry(times=2, delay=5, factor=2)(color.download_image_from_geoplateforme)
    with pytest.raises(requests.exceptions.HTTPError):
        retry_download(EPSG, "MAUVAISE_COUCHE", MINX, MINY, MAXX, MAXY, 100, 100, OUTPUT_FILE, 15, True)


@pytest.mark.geopf
def test_download_image_raise2():
    retry_download = color.retry(times=2, delay=5, factor=2)(color.download_image_from_geoplateforme)
    with pytest.raises(requests.exceptions.HTTPError):
        retry_download("9001", LAYER, MINX, MINY, MAXX, MAXY, 100, 100, OUTPUT_FILE, 15, True)


def test_retry_on_server_error():
    with requests_mock.Mocker() as mock:
        mock.get(requests_mock.ANY, status_code=502, reason="Bad Gateway")
        with pytest.raises(requests.exceptions.HTTPError):
            retry_download = color.retry(times=2, delay=1, factor=2)(color.download_image_from_geoplateforme)
            retry_download(EPSG, LAYER, MINX, MINY, MAXX, MAXY, 100, 100, OUTPUT_FILE, 15, True)
        history = mock.request_history
        assert len(history) == 3


def test_retry_on_connection_error():
    with requests_mock.Mocker() as mock:
        mock.get(requests_mock.ANY, exc=requests.exceptions.ConnectionError)
        with pytest.raises(requests.exceptions.ConnectionError):
            retry_download = color.retry(times=2, delay=1, factor=2)(color.download_image_from_geoplateforme)
            retry_download(EPSG, LAYER, MINX, MINY, MAXX, MAXY, 100, 100, OUTPUT_FILE, 15, True)

        history = mock.request_history
        assert len(history) == 3


def test_retry_param():
    # Here you can change retry params
    @color.retry(times=9, delay=5, factor=2, debug=True)
    def raise_server_error():
        raise requests.exceptions.HTTPError("Server Error")

    with pytest.raises(requests.exceptions.HTTPError):
        raise_server_error()
