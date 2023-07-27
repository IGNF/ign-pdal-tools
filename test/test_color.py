import os
import shutil
import pytest

from pdaltools import color

import requests
import requests_mock

cwd = os.getcwd()

TMPDIR = cwd + "/tmp/"

def setup_module(module):
    try:
        shutil.rmtree(TMPDIR)
    except (FileNotFoundError):
        pass
    os.mkdir(TMPDIR)

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(TEST_PATH, 'data/test_noepsg_043500_629205_IGN69.laz')

OUTPUT_FILE = TMPDIR + "Semis_2021_0435_6292_LA93_IGN69.las"


@pytest.mark.geoportail
def test_epsg_fail():
    with pytest.raises(requests.exceptions.HTTPError, match="400 Client Error: BadRequest for url") :
        color.color(INPUT_PATH, OUTPUT_FILE, "", 0.1, 15)


epsg = "2154"
layer= "ORTHOIMAGERY.ORTHOPHOTOS"
minx=435000
miny=6291000
maxx=436000
maxy=6292000
pixel_per_meter=0.1


@pytest.mark.geoportail
def test_download_image_ok():
    color.download_image_from_geoportail(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15)


@pytest.mark.geoportail
def test_download_image_raise1():
    retry_download = color.retry(2, 5)(color.download_image_from_geoportail)
    with pytest.raises(requests.exceptions.HTTPError):
        retry_download(epsg, "MAUVAISE_COUCHE", minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15)


@pytest.mark.geoportail
def test_download_image_raise2():
    retry_download = color.retry(2, 5)(color.download_image_from_geoportail)
    with pytest.raises(requests.exceptions.HTTPError):
        retry_download("9001", layer, minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15)


def test_retry_on_server_error():
    with requests_mock.Mocker() as mock:
        mock.get(requests_mock.ANY, status_code=502, reason="Bad Gateway")
        with pytest.raises(requests.exceptions.HTTPError):
            retry_download = color.retry(2, 1, 2)(color.download_image_from_geoportail)
            retry_download(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, OUTPUT_FILE, 15)
        history = mock.request_history
        assert len(history) == 3


def test_retry_on_connection_error():
      with requests_mock.Mocker() as mock:
        mock.get(requests_mock.ANY, exc=requests.exceptions.ConnectionError)
        with pytest.raises(requests.exceptions.ConnectionError):
            retry_download = color.retry(2, 1)(color.download_image_from_geoportail)
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
