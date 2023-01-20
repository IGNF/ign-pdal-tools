import os
import shutil
import pytest
import requests
import laspy

from tools import color

cwd = os.getcwd()

TMPDIR = cwd + "/tmp/"


def setup_module(module):
    try:
        shutil.rmtree(TMPDIR)

    except (FileNotFoundError):
        pass
    os.mkdir(TMPDIR)

input_file = "/var/data/store-lidarhd/developpement/lidarexpress/tests/test_bug_laz_epsg/epsg_fail/Semis_2021_0435_6292_LA93_IGN69.laz"
ouptput_file = TMPDIR + "Semis_2021_0435_6292_LA93_IGN69.las"


# @pytest.mark.skip("tmp")
def test_epsg_fail():

    with pytest.raises(requests.exceptions.HTTPError, match="400 Client Error: BadRequest for url") :
        color.decomp_and_color(input_file, ouptput_file, "", 0.1, 15)


epsg = "2154"
layer= "ORTHOIMAGERY.ORTHOPHOTOS"
minx=435000
miny=6291000
maxx=436000
maxy=6292000
pixel_per_meter=0.1


# @pytest.mark.skip("tmp dev")
def test_download_image_ok():
    color.download_image_from_geoportail(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, ouptput_file, 15)


# @pytest.mark.skip("tmp dev")
def test_download_image_raise1():

    with pytest.raises(requests.exceptions.HTTPError):
        color.download_image_from_geoportail(epsg, "MAUVAISE_COUCHE", minx, miny, maxx, maxy, pixel_per_meter, ouptput_file, 15)


# @pytest.mark.skip("tmp dev")
def test_download_image_raise2():

    with pytest.raises(requests.exceptions.HTTPError):
        color.download_image_from_geoportail("9001", layer, minx, miny, maxx, maxy, pixel_per_meter, ouptput_file, 15)


# Pour bien tester ceci, il faut debrancher son cable réseau et voir que la méthode est bien appellée 3 fois, toutes les 5 secondes
# @pytest.mark.skip("tmp dev")
def test_retry():
    retry_download = color.retry(3, 5)(color.download_image_from_geoportail)
    retry_download(epsg, layer, minx, miny, maxx, maxy, pixel_per_meter, ouptput_file, 15)


@pytest.mark.skip("TODO: utiliser un fichier sur le store")
def test_decomp_and_color():

    # bug de l'ouverture des laz
    # TODO Faire une version legere de ce LAZ et le mettre sur le git
    LAZ_FILE = "/media/data/Bug_ouverture_laz/one/436000_6469000.laz"
    LAS_FILE = TMPDIR + "436000_6469000.las"

    color.decomp_and_color(LAZ_FILE, LAS_FILE, "", 0.1)

    las = laspy.read(LAS_FILE)
    print(las.header)
    print(list(las.point_format.dimension_names))
    print(las.red)
    print(las.green)
    print(las.blue)
    print(las.nir)

    assert os.path.isfile(LAS_FILE)
