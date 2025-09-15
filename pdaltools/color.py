import argparse
import tempfile
from math import ceil, floor
from typing import Tuple

import pdal

import pdaltools.las_info as las_info
from pdaltools.download_image import download_image


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
    vegetation_dim="Deviation",
    check_images=False,
    stream_RGB="ORTHOIMAGERY.ORTHOPHOTOS",
    stream_IRC="ORTHOIMAGERY.ORTHOPHOTOS.IRC",
    size_max_gpf=5000,
):
    """Colorize a las file with any of the following methods:
    - R, G, B values from an image retrieved from ign geoplateform via the "stream_RGB" data feed name
    - Infrared from another image retrieved from ign geoplateform via the "stream_IRC" data feed name
    - any field "vegetation_dim" from another image stored locally at "veget_index_file"


    Args:
        input_file (str): Path to the las file to colorize
        output_file (str): Path to the output colorized file
        proj (str, optional): EPSG value of the SRS to apply to the output file (if not provided, use the one from
        the input file). Eg. "2154" to use "EPSG:2154". Defaults to "".
        pixel_per_meter (int, optional): Stream image resolution (for RGB and IRC) in pixels per meter. Defaults to 5.
        timeout_second (int, optional): Timeout for the geoplateform request. Defaults to 300.
        color_rvb_enabled (bool, optional): If true, apply R, G, B dimensions colorization. Defaults to True.
        color_ir_enabled (bool, optional): If true, apply Infrared dimension colorization. Defaults to True.
        veget_index_file (str, optional): Path to the tiff tile to use for "vegetation_dim" colorization.
        Defaults to "".
        vegetation_dim (str, optional): Name of the dimension to use to store the values of "veget_index_file".
        Defaults to "Deviation".
        check_images (bool, optional): If true, check if images from the geoplateform data feed are white
        (and raise and error in this case). Defaults to False.
        stream_RGB (str, optional): WMS raster stream for RGB colorization:
        Default stream (ORTHOIMAGERY.ORTHOPHOTOS) let the server choose the resolution
        for 20cm resolution rasters, use HR.ORTHOIMAGERY.ORTHOPHOTOS
        for 50 cm resolution rasters, use ORTHOIMAGERY.ORTHOPHOTOS.BDORTHO
        Defaults to ORTHOIMAGERY.ORTHOPHOTOS
        stream_IRC (str, optional):WMS raster stream for IRC colorization.
        Documentation about possible stream : https://geoservices.ign.fr/services-web-experts-ortho.
        Defaults to "ORTHOIMAGERY.ORTHOPHOTOS.IRC".
        size_max_gpf (int, optional): Maximum edge size (in pixels) of downloaded images. If input file needs more,
        several images are downloaded and merged. Defaults to 5000.

    Returns:
        Paths to the temporary files that store the streamed images (tmp_ortho, tmp_ortho_irc)
    """
    metadata = las_info.las_info_metadata(input_file)
    minx, maxx, miny, maxy = las_info.get_bounds_from_header_info(metadata)

    minx, maxx = match_min_max_with_pixel_size(minx, maxx, pixel_per_meter)
    miny, maxy = match_min_max_with_pixel_size(miny, maxy, pixel_per_meter)

    if proj == "":
        proj = las_info.get_epsg_from_header_info(metadata)

    pipeline = pdal.Reader.las(filename=input_file)

    writer_extra_dims = "all"

    if veget_index_file and veget_index_file != "":
        print(f"Remplissage du champ {vegetation_dim} à partir du fichier {veget_index_file}")
        pipeline |= pdal.Filter.colorization(raster=veget_index_file, dimensions=f"{vegetation_dim}:1:256.0")
        writer_extra_dims = [f"{vegetation_dim}=ushort"]

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
        "--vegetation",
        type=str,
        default="",
        help="Vegetation file (raster), value will be stored in 'vegetation_dim' field",
    )
    parser.add_argument(
        "--vegetation_dim", type=str, default="Deviation", help="name of the extra_dim uses for the vegetation value"
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
        vegetation_dim=args.vegetation_dim,
        check_images=args.check_images,
        stream_RGB=args.stream_RGB,
        stream_IRC=args.stream_IRC,
        size_max_gpf=args.size_max_GPF,
    )
