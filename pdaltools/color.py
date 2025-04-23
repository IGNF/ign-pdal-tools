import argparse
import tempfile
import time
from math import ceil, floor
from pathlib import Path
from typing import Tuple

import numpy as np
import pdal
import requests
from osgeo import gdal, gdal_array

import pdaltools.las_info as las_info
from pdaltools.unlock_file import copy_and_hack_decorator


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


def match_min_max_with_pixel_size(min_d: float, max_d: float, pixel_per_meter: float) -> Tuple[float, float]:
    """Round min/max values along one dimension to the closest multiple of 1 / pixel_per_meter
    It should prevent having to interpolate during a request to the geoplateforme
    in case we use a native resolution.

    Args:
        min_d (float): minimum value along the dimension, in meters
        max_d (float): maximum value along the dimension, in meters
        pixel_per_meter (float): resolution (in number of pixels per meter)

    Returns:
        Tuple[float, float]: adapted min / max value
    """
    # Use ceil - 1 instead of ceil  to make sure that
    # no point of the pointcloud is on the limit of the first pixel
    min_d = (ceil(min_d * pixel_per_meter) - 1) / pixel_per_meter
    # Use floor + 1 instead of ceil to make sure that no point of the pointcloud is on the limit of the last pixel
    max_d = (floor(max_d * pixel_per_meter) + 1) / pixel_per_meter

    return min_d, max_d


def color(
    input_file: str,
    output_file: str,
    proj="",
    pixel_per_meter=5,
    timeout_second=300,
    color_rvb_enabled=True,
    color_ir_enabled=True,
    veget_index_file="",
    check_images=False,
    stream_RGB="ORTHOIMAGERY.ORTHOPHOTOS",
    stream_IRC="ORTHOIMAGERY.ORTHOPHOTOS.IRC",
    size_max_gpf=5000,
):
    metadata = las_info.las_info_metadata(input_file)
    minx, maxx, miny, maxy = las_info.get_bounds_from_header_info(metadata)

    minx, maxx = match_min_max_with_pixel_size(minx, maxx, pixel_per_meter)
    miny, maxy = match_min_max_with_pixel_size(miny, maxy, pixel_per_meter)

    if proj == "":
        proj = las_info.get_epsg_from_header_info(metadata)

    pipeline = pdal.Reader.las(filename=input_file)

    writer_extra_dims = "all"

    if veget_index_file and veget_index_file != "":
        print(f"Remplissage du champ Deviation à partir du fichier {veget_index_file}")
        pipeline |= pdal.Filter.colorization(raster=veget_index_file, dimensions="Deviation:1:256.0")
        writer_extra_dims = ["Deviation=ushort"]

    tmp_ortho = None
    if color_rvb_enabled:
        tmp_ortho = tempfile.NamedTemporaryFile(suffix="_rvb.tif")
        download_image(
            proj,
            stream_RGB,
            minx,
            miny,
            maxx,
            maxy,
            pixel_per_meter,
            tmp_ortho.name,
            timeout_second,
            check_images,
            size_max_gpf,
        )
        # Warning: the initial color is multiplied by 256 despite its initial 8-bits encoding
        # which turns it to a 0 to 255*256 range.
        # It is kept this way because of other dependencies that have been tuned to fit this range
        pipeline |= pdal.Filter.colorization(
            raster=tmp_ortho.name, dimensions="Red:1:256.0, Green:2:256.0, Blue:3:256.0"
        )

    tmp_ortho_irc = None
    if color_ir_enabled:
        tmp_ortho_irc = tempfile.NamedTemporaryFile(suffix="_irc.tif")
        download_image(
            proj,
            stream_IRC,
            minx,
            miny,
            maxx,
            maxy,
            pixel_per_meter,
            tmp_ortho_irc.name,
            timeout_second,
            check_images,
            size_max_gpf,
        )
        # Warning: the initial color is multiplied by 256 despite its initial 8-bits encoding
        # which turns it to a 0 to 255*256 range.
        # It is kept this way because of other dependencies that have been tuned to fit this range
        pipeline |= pdal.Filter.colorization(raster=tmp_ortho_irc.name, dimensions="Infrared:1:256.0")

    pipeline |= pdal.Writer.las(
        filename=output_file, extra_dims=writer_extra_dims, minor_version="4", dataformat_id="8", forward="all"
    )

    print("Traitement du nuage de point")
    pipeline.execute()

    # The orthoimages files will be deleted only when their reference are lost.
    # To keep them, make a copy (with e.g. shutil.copy(...))
    # See: https://docs.python.org/2/library/tempfile.html#tempfile.TemporaryFile
    return tmp_ortho, tmp_ortho_irc


def parse_args():
    parser = argparse.ArgumentParser("Colorize tool", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--input", "-i", type=str, required=True, help="Input file")
    parser.add_argument("--output", "-o", type=str, default="", help="Output file")
    parser.add_argument(
        "--proj", "-p", type=str, default="", help="Projection, default will use projection from metadata input"
    )
    parser.add_argument("--resolution", "-r", type=float, default=5, help="Resolution, in pixel per meter")
    parser.add_argument("--timeout", "-t", type=int, default=300, help="Timeout, in seconds")
    parser.add_argument("--rvb", action="store_true", help="Colorize RVB")
    parser.add_argument("--ir", action="store_true", help="Colorize IR")
    parser.add_argument(
        "--vegetation", type=str, default="", help="Vegetation file, value will be stored in Deviation field"
    )
    parser.add_argument("--check-images", "-c", action="store_true", help="Check that downloaded image is not white")
    parser.add_argument(
        "--stream-RGB",
        type=str,
        default="ORTHOIMAGERY.ORTHOPHOTOS",
        help="""WMS raster stream for RGB colorization:
default stream (ORTHOIMAGERY.ORTHOPHOTOS) let the server choose the resolution
for 20cm resolution rasters, use HR.ORTHOIMAGERY.ORTHOPHOTOS
for 50 cm resolution rasters, use ORTHOIMAGERY.ORTHOPHOTOS.BDORTHO""",
    )
    parser.add_argument(
        "--stream-IRC",
        type=str,
        default="ORTHOIMAGERY.ORTHOPHOTOS.IRC",
        help="""WMS raster stream for IRC colorization. Default to ORTHOIMAGERY.ORTHOPHOTOS.IRC
Documentation about possible stream : https://geoservices.ign.fr/services-web-experts-ortho""",
    )
    parser.add_argument(
        "--size-max-GPF",
        type=int,
        default=5000,
        help="Maximum edge size (in pixels) of downloaded images."
        " If input file needs more, several images are downloaded and merged.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    color(
        input_file=args.input,
        output_file=args.output,
        proj=args.proj,
        pixel_per_meter=args.resolution,
        timeout_second=args.timeout,
        color_rvb_enabled=args.rvb,
        color_ir_enabled=args.ir,
        veget_index_file=args.vegetation,
        check_images=args.check_images,
        stream_RGB=args.stream_RGB,
        stream_IRC=args.stream_IRC,
        size_max_gpf=args.size_max_GPF,
    )
