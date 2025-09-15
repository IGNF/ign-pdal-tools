"""Tool to download an image from IGN geoplateform: https://geoservices.ign.fr/"""

import tempfile
import time
from math import ceil
from pathlib import Path
from typing import Tuple

import numpy as np
import requests
from osgeo import gdal, gdal_array

from pdaltools.unlock_file import copy_and_hack_decorator


def compute_cells_size(mind: float, maxd: float, pixel_per_meter: float, size_max_gpf: int) -> Tuple[int, int, int]:
    """Compute cell size to have cells of almost equal size, but phased the same way as
    if there had been no paving by forcing cell_size (in pixels) to be an integer

    Args:
        mind (float): minimum value along the dimension, in meters
        maxd (float): maximum value along the dimension, in meters
        pixel_per_meter (float): resolution (in number of pixels per meter)
        size_max_gpf (int): maximum image size in pixels

    Returns:
        Tuple[int, int, int]: number of pixels in total, number of cells along the dimension, cell size in pixels
    """
    nb_pixels = ceil((maxd - mind) * pixel_per_meter)
    nb_cells = ceil(nb_pixels / size_max_gpf)
    cell_size_pixels = ceil(nb_pixels / nb_cells)  # Force cell size to be an integer

    return nb_pixels, nb_cells, cell_size_pixels


def is_image_white(filename: str):
    raster_array = gdal_array.LoadFile(filename)
    band_is_white = [np.all(band == 255) for band in raster_array]
    return np.all(band_is_white)


def download_image_from_geoplateforme(
    proj, layer, minx, miny, maxx, maxy, width_pixels, height_pixels, outfile, timeout, check_images
):
    """
    Download image using a wms request to geoplateforme.

    Args:
      proj (int): epsg code for the projection of the downloaded image.
      layer: which kind of image is downloaded (ORTHOIMAGERY.ORTHOPHOTOS, ORTHOIMAGERY.ORTHOPHOTOS.IRC, ...).
      minx, miny, maxx, maxy: box of the downloaded image.
      width_pixels:  width in pixels of the downloaded image.
      height_pixels:  height in pixels of the downloaded image.
      outfile: file name of the downloaded file
      timeout: delay after which the request is canceled (in seconds)
      check_images (bool): enable checking if the output image is not a white image
    """

    # for layer in layers:
    URL_GPP = "https://data.geopf.fr/wms-r/wms?"
    URL_FORMAT = "&EXCEPTIONS=text/xml&FORMAT=image/geotiff&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES="
    URL_EPSG = "&CRS=EPSG:" + str(proj)
    URL_BBOX = "&BBOX=" + str(minx) + "," + str(miny) + "," + str(maxx) + "," + str(maxy)
    URL_SIZE = "&WIDTH=" + str(width_pixels) + "&HEIGHT=" + str(height_pixels)

    URL = URL_GPP + "LAYERS=" + layer + URL_FORMAT + URL_EPSG + URL_BBOX + URL_SIZE

    print(URL)
    if timeout < 10:
        print(f"Mode debug avec un timeout à {timeout} secondes")

    req = requests.get(URL, allow_redirects=True, timeout=timeout)
    req.raise_for_status()
    print(f"Ecriture du fichier: {outfile}")
    open(outfile, "wb").write(req.content)

    if check_images and is_image_white(outfile):
        raise ValueError(f"Downloaded image is white, with stream: {layer}")


def pretty_time_delta(seconds):
    sign_string = "-" if seconds < 0 else ""
    seconds = abs(int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return "%s%dd%dh%dm%ds" % (sign_string, days, hours, minutes, seconds)
    elif hours > 0:
        return "%s%dh%dm%ds" % (sign_string, hours, minutes, seconds)
    elif minutes > 0:
        return "%s%dm%ds" % (sign_string, minutes, seconds)
    else:
        return "%s%ds" % (sign_string, seconds)


def retry(times, delay, factor, debug=False):
    def decorator(func):
        def newfn(*args, **kwargs):
            attempt = 1
            new_delay = delay
            while attempt <= times:
                need_retry = False
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as err:
                    print("Connection Error:", err)
                    need_retry = True
                if need_retry:
                    print(f"{attempt}/{times} Nouvel essai après une pause de {pretty_time_delta(new_delay)} .. ")
                    if not debug:
                        time.sleep(new_delay)
                    new_delay = new_delay * factor
                    attempt += 1

            return func(*args, **kwargs)

        return newfn

    return decorator


@copy_and_hack_decorator
def download_image(proj, layer, minx, miny, maxx, maxy, pixel_per_meter, outfile, timeout, check_images, size_max_gpf):
    """
    Download image using a wms request to geoplateforme with call of download_image_from_geoplateforme() :
    image are downloaded in blocks then merged, in order to limit the size of geoplateforme requests.

    Args:
      proj: projection of the downloaded image.
      layer: which kind of image is downloaed (ORTHOIMAGERY.ORTHOPHOTOS, ORTHOIMAGERY.ORTHOPHOTOS.IRC, ...).
      minx, miny, maxx, maxy: box of the downloaded image.
      pixel_per_meter: resolution of the downloaded image.
      outfile: file name of the downloaed file
      timeout: time after the request is canceled
      check_images: check if images is not a white image
      size_max_gpf: block size of downloaded images. (in pixels)

    return the number of effective requests
    """

    download_image_from_geoplateforme_retrying = retry(times=9, delay=5, factor=2)(download_image_from_geoplateforme)

    size_x_p, nb_cells_x, cell_size_x = compute_cells_size(minx, maxx, pixel_per_meter, size_max_gpf)
    size_y_p, nb_cells_y, cell_size_y = compute_cells_size(minx, maxx, pixel_per_meter, size_max_gpf)

    # the image size is under SIZE_MAX_IMAGE_GPF
    if (size_x_p <= size_max_gpf) and (size_y_p <= size_max_gpf):
        download_image_from_geoplateforme_retrying(
            proj, layer, minx, miny, maxx, maxy, cell_size_x, cell_size_y, outfile, timeout, check_images
        )
        return 1

    # the image is bigger than the SIZE_MAX_IMAGE_GPF
    # it's preferable to compute it by paving
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_gpg_ortho = []
        for line in range(0, nb_cells_y):
            for col in range(0, nb_cells_x):
                # Cope for last line/col that can be slightly smaller than other cells
                remaining_pixels_x = size_x_p - col * cell_size_x
                remaining_pixels_y = size_y_p - line * cell_size_y
                cell_size_x_local = min(cell_size_x, remaining_pixels_x)
                cell_size_y_local = min(cell_size_y, remaining_pixels_y)

                minx_cell = minx + col * cell_size_x / pixel_per_meter
                maxx_cell = minx_cell + cell_size_x_local / pixel_per_meter
                miny_cell = miny + line * cell_size_y / pixel_per_meter
                maxy_cell = miny_cell + cell_size_y_local / pixel_per_meter

                cells_ortho_paths = str(Path(tmp_dir)) + f"cell_{col}_{line}.tif"
                download_image_from_geoplateforme_retrying(
                    proj,
                    layer,
                    minx_cell,
                    miny_cell,
                    maxx_cell,
                    maxy_cell,
                    cell_size_x_local,
                    cell_size_y_local,
                    cells_ortho_paths,
                    timeout,
                    check_images,
                )
                tmp_gpg_ortho.append(cells_ortho_paths)

        # merge the cells
        with tempfile.NamedTemporaryFile(suffix="_gpf.vrt") as tmp_vrt:
            gdal.BuildVRT(tmp_vrt.name, tmp_gpg_ortho)
            gdal.Translate(outfile, tmp_vrt.name)

    return nb_cells_x * nb_cells_y
