import os
import shutil
from pathlib import Path

import pytest
import requests
import requests_mock

from pdaltools import color

cwd = os.getcwd()

TMPDIR = cwd + "/tmp/"


def setup_module(module):
    try:
        shutil.rmtree(TMPDIR)
    except FileNotFoundError:
        pass
    os.mkdir(TMPDIR)


TEST_PATH = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(TEST_PATH, "data/test_noepsg_043500_629205_IGN69.laz")
INPUT_PATH_SINGLE_POINT_CLOUD = os.path.join(TEST_PATH, "data/test_data_0436_6384_LA93_IGN69_single_point.laz")

OUTPUT_FILE = TMPDIR + "Semis_2021_0435_6292_LA93_IGN69.las"
OUTPUT_FILE_SINGLE_POINT_CLOUD = TMPDIR + "test_data_0436_6384_LA93_IGN69_single_point.colorized.laz"


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


@pytest.mark.geopf
def test_color_and_keeping_orthoimages():
    tmp_ortho, tmp_ortho_irc = color.color(INPUT_PATH, OUTPUT_FILE, epsg)
    assert Path(tmp_ortho.name).exists()
    assert Path(tmp_ortho_irc.name).exists()


@pytest.mark.geopf
def test_color_narrow_cloud():
    # Test that clouds that are smaller in width or height to 20cm are still clorized without an error.
    color.color(INPUT_PATH_SINGLE_POINT_CLOUD, OUTPUT_FILE_SINGLE_POINT_CLOUD, epsg)


@pytest.mark.geopf
def test_download_image_ok():
    color.download_image_from_geoplateforme(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15)


@pytest.mark.geopf
def test_download_image_raise1():
    retry_download = color.retry(2, 5)(color.download_image_from_geoplateforme)
    with pytest.raises(requests.exceptions.HTTPError):
        retry_download(epsg, "MAUVAISE_COUCHE", minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15)


@pytest.mark.geopf
def test_download_image_raise2():
    retry_download = color.retry(2, 5)(color.download_image_from_geoplateforme)
    with pytest.raises(requests.exceptions.HTTPError):
        retry_download("9001", layer, minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15)


def test_retry_on_server_error():
    with requests_mock.Mocker() as mock:
        mock.get(requests_mock.ANY, status_code=502, reason="Bad Gateway")
        with pytest.raises(requests.exceptions.HTTPError):
            retry_download = color.retry(2, 1, 2)(color.download_image_from_geoplateforme)
            retry_download(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15)
        history = mock.request_history
        assert len(history) == 3


def test_retry_on_connection_error():
    with requests_mock.Mocker() as mock:
        mock.get(requests_mock.ANY, exc=requests.exceptions.ConnectionError)
        with pytest.raises(requests.exceptions.ConnectionError):
            retry_download = color.retry(2, 1)(color.download_image_from_geoplateforme)
            retry_download(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15)

        history = mock.request_history
        assert len(history) == 3


def test_retry_param():
    # Here you can change retry params
    @color.retry(7, 15, 2, True)
    def raise_server_error():
        raise requests.exceptions.HTTPError("Server Error")

    with pytest.raises(requests.exceptions.HTTPError):
        raise_server_error()
