import math
import os
import shutil
from pathlib import Path

import numpy
import pytest
import requests
import requests_mock
from osgeo import gdal

from pdaltools import color

cwd = os.getcwd()

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMPDIR = os.path.join(TEST_PATH, "tmp")


def setup_module(module):
    try:
        shutil.rmtree(TMPDIR)
    except FileNotFoundError:
        pass
    os.mkdir(TMPDIR)


INPUT_PATH = os.path.join(TEST_PATH, "data/test_noepsg_043500_629205_IGN69.laz")

OUTPUT_FILE = os.path.join(TMPDIR, "Semis_2021_0435_6292_LA93_IGN69.colorized.las")


@pytest.mark.geopf
def test_epsg_fail():
    with pytest.raises(
        RuntimeError,
        match="EPSG could not be inferred from metadata: No 'srs' key in metadata.",
    ):
        color.color(INPUT_PATH, OUTPUT_FILE, "", 0.1, 15)


epsg = "2154"
layer = "ORTHOIMAGERY.ORTHOPHOTOS"
minx = 435000
miny = 6291000
maxx = 436000
maxy = 6292000
pixel_per_meter = 0.1
size_max_image_gpf = 500


@pytest.mark.geopf
def test_color_and_keeping_orthoimages():
    tmp_ortho, tmp_ortho_irc = color.color(INPUT_PATH, OUTPUT_FILE, epsg, check_images=True)
    assert Path(tmp_ortho.name).exists()
    assert Path(tmp_ortho_irc.name).exists()


@pytest.mark.geopf
def test_color_narrow_cloud():
    input_path = os.path.join(TEST_PATH, "data/test_data_0436_6384_LA93_IGN69_single_point.laz")
    output_path = os.path.join(TMPDIR, "test_data_0436_6384_LA93_IGN69_single_point.colorized.laz")
    # Test that clouds that are smaller in width or height to 20cm are still clorized without an error.
    color.color(input_path, output_path, epsg)


@pytest.mark.geopf
def test_download_image_ok():
    tif_output = os.path.join(TMPDIR, "download_image.tif")
    color.download_image(
        epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, tif_output, 15, True, size_max_image_gpf
    )

    # check there is no noData
    raster = gdal.Open(tif_output)
    for i in range(raster.RasterCount):
        assert raster.GetRasterBand(i + 1).GetNoDataValue() is None


@pytest.mark.geopf
def test_download_image_ok_one_download():
    tif_output = os.path.join(TMPDIR, "download_image.tif")
    nb_request = color.download_image(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, tif_output, 15, True, 1000)
    assert nb_request == 1

    # check there is no noData
    raster = gdal.Open(tif_output)
    for i in range(raster.RasterCount):
        assert raster.GetRasterBand(i + 1).GetNoDataValue() is None


@pytest.mark.geopf
def test_download_image_download_size_gpf_bigger():
    tif_output = os.path.join(TMPDIR, "download_image_bigger.tif")
    color.download_image(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, tif_output, 15, True, 1005)

    # check there is no noData
    raster = gdal.Open(tif_output)
    for i in range(raster.RasterCount):
        assert raster.GetRasterBand(i + 1).GetNoDataValue() is None


@pytest.mark.geopf
def test_download_image_download_size_gpf_size_almost_ok():
    tif_output = os.path.join(TMPDIR, "download_image_bigger.tif")
    nb_request = color.download_image(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, tif_output, 15, True, 995)
    assert nb_request == 4

    # check there is no noData
    raster = gdal.Open(tif_output)
    for i in range(raster.RasterCount):
        assert raster.GetRasterBand(i + 1).GetNoDataValue() is None


@pytest.mark.parametrize("size_block", [100, 250, 500])
def test_download_image_one_and_block(size_block):
    tif_output_one = os.path.join(TMPDIR, "download_image_one.tif")
    color.download_image(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, tif_output_one, 15, True, 1000)

    tif_output_blocks = os.path.join(TMPDIR, "download_image_block.tif")
    nb_request = color.download_image(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, tif_output_blocks, 100, True, size_block)
    assert nb_request == math.pow(1000/size_block, 2)

    # due to GeoPlateforme interpolation, images could have small differences
    # check images are almost the sames

    raster_one = gdal.Open(tif_output_one)
    raster_blocks = gdal.Open(tif_output_blocks)

    r_one = numpy.array(raster_one.ReadAsArray())
    r_blocks = numpy.array(raster_blocks.ReadAsArray())
    assert r_one.size == r_blocks.size
    r_diff = r_one - r_blocks

    # images should be same as 5/1000 (tolerance)
    assert numpy.count_nonzero(r_diff) < 0.005 * ((maxx - minx) * (maxy - miny) * math.pow(pixel_per_meter, 2))

    # differences should be 1 or 255 (eq a variation of one on one RVB canal)
    r_diff_nonzero = numpy.nonzero(r_diff)
    for i in range(0, r_diff_nonzero[0].size):
        diff = r_diff[r_diff_nonzero[0][i], r_diff_nonzero[1][i], r_diff_nonzero[2][i]]
        assert diff == 1 or diff == 255


@pytest.mark.geopf
def test_color_epsg_2975_forced():
    input_path = os.path.join(TEST_PATH, "data/sample_lareunion_epsg2975.laz")
    output_path = os.path.join(TMPDIR, "sample_lareunion_epsg2975.colorized.laz")
    # Test that clouds that are smaller in width or height to 20cm are still clorized without an error.
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
    output_path = os.path.join(TMPDIR, "sample_lareunion_epsg2975.colorized.laz")
    # Test that clouds that are smaller in width or height to 20cm are still clorized without an error.
    color.color(input_path, output_path)


@pytest.mark.geopf
def test_download_image_raise1():
    retry_download = color.retry(2, 5)(color.download_image_from_geoplateforme)
    with pytest.raises(requests.exceptions.HTTPError):
        retry_download(epsg, "MAUVAISE_COUCHE", minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15, True)


@pytest.mark.geopf
def test_download_image_raise2():
    retry_download = color.retry(2, 5)(color.download_image_from_geoplateforme)
    with pytest.raises(requests.exceptions.HTTPError):
        retry_download("9001", layer, minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15, True)


def test_retry_on_server_error():
    with requests_mock.Mocker() as mock:
        mock.get(requests_mock.ANY, status_code=502, reason="Bad Gateway")
        with pytest.raises(requests.exceptions.HTTPError):
            retry_download = color.retry(2, 1, 2)(color.download_image_from_geoplateforme)
            retry_download(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15, True)
        history = mock.request_history
        assert len(history) == 3


def test_retry_on_connection_error():
    with requests_mock.Mocker() as mock:
        mock.get(requests_mock.ANY, exc=requests.exceptions.ConnectionError)
        with pytest.raises(requests.exceptions.ConnectionError):
            retry_download = color.retry(2, 1)(color.download_image_from_geoplateforme)
            retry_download(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15, True)

        history = mock.request_history
        assert len(history) == 3


def test_retry_param():
    # Here you can change retry params
    @color.retry(9, 5, 2, True)
    def raise_server_error():
        raise requests.exceptions.HTTPError("Server Error")

    with pytest.raises(requests.exceptions.HTTPError):
        raise_server_error()
