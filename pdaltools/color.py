import json
import subprocess as sp
import tempfile
import pdal
import requests
from osgeo.osr import SpatialReference
import time
import argparse

from pdaltools.unlock_file import copy_and_hack_decorator


def pretty_time_delta(seconds):
    sign_string = '-' if seconds < 0 else ''
    seconds = abs(int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return '%s%dd%dh%dm%ds' % (sign_string, days, hours, minutes, seconds)
    elif hours > 0:
        return '%s%dh%dm%ds' % (sign_string, hours, minutes, seconds)
    elif minutes > 0:
        return '%s%dm%ds' % (sign_string, minutes, seconds)
    else:
        return '%s%ds' % (sign_string, seconds)


def retry(times, delay, factor=2, debug=False):
    def decorator(func):
        def newfn(*args, **kwargs):
            attempt = 1
            new_delay = delay
            while attempt <= times:
                need_retry = False
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.ConnectionError as err:
                    print ("Connection Error:", err)
                    need_retry = True
                except requests.exceptions.HTTPError as err:
                    if "Server Error" in str(err):
                        print ("HTTP Error:", err)
                        need_retry = True
                    else:
                        raise err
                if need_retry:
                    print(f"{attempt}/{times} Nouvel essai après une pause de {pretty_time_delta(new_delay)} .. ")
                    if not debug:
                        time.sleep(new_delay)
                    new_delay = new_delay * factor
                    attempt += 1

            return func(*args, **kwargs)
        return newfn
    return decorator


def download_image_from_geoportail(
    proj, layer, minx, miny, maxx, maxy, pixel_per_meter, outfile, timeout
):
    # for layer in layers:
    URL_GPP = "https://wxs.ign.fr/ortho/geoportail/r/wms?"
    URL_FORMAT = "&EXCEPTIONS=text/xml&FORMAT=image/geotiff&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES="
    URL_EPSG = "&CRS=EPSG:" + str(proj)
    URL_BBOX = (
        "&BBOX=" + str(minx) + "," + str(miny) + "," + str(maxx) + "," + str(maxy)
    )
    URL_SIZE = (
        "&WIDTH="
        + str(int((maxx - minx) * pixel_per_meter))
        + "&HEIGHT="
        + str(int((maxy - miny) * pixel_per_meter))
    )

    URL = URL_GPP + "LAYERS=" + layer + URL_FORMAT + URL_EPSG + URL_BBOX + URL_SIZE

    print(URL)
    if timeout < 10:
        print(f"Mode debug avec un timeout à {timeout} secondes")

    req = requests.get(URL, allow_redirects=True, timeout=timeout)
    req.raise_for_status()
    print(f"Ecriture du fichier: {outfile}")
    open(outfile, "wb").write(req.content)


def proj_from_metadata(metadata):
    spatial_wkt = metadata["comp_spatialreference"]
    osr_crs = SpatialReference()
    osr_crs.ImportFromWkt(spatial_wkt)
    authority = osr_crs.GetAttrValue("AUTHORITY", 0)
    if authority == "EPSG":
        proj = osr_crs.GetAttrValue("AUTHORITY", 1)
    else:
        proj = "2154"  # par defaut
    return proj


def pdal_info_json(input_file: str):
    r = sp.run(["pdal", "info", "--metadata", input_file], stderr=sp.PIPE, stdout=sp.PIPE)
    if r.returncode == 1:
        msg = r.stderr.decode()
        print(msg)
        raise RuntimeError(msg)

    output = r.stdout.decode()
    json_info = {}
    try:
        json_info = json.loads(output)
    except:
        print(r.stderr.decode())
        raise
    return json_info


@copy_and_hack_decorator
def color(input_file: str, output_file :str,
    proj="", pixel_per_meter=5, timeout_second=300,
    color_rvb_enabled=True, color_ir_enabled=True, veget_index_file=""
    ):

    json_info = pdal_info_json(input_file)
    metadata = json_info["metadata"]
    minx, maxx, miny, maxy = metadata["minx"], metadata["maxx"], metadata["miny"], metadata["maxy"]

    if proj == "":
        proj = proj_from_metadata(metadata)

    pipeline = pdal.Reader.las(filename=input_file)

    writer_extra_dims = "all"

    # apply decorator to retry 3 times, and wait 30 seconds each times
    download_image_from_geoportail_retrying = retry(7, 15, 2)(download_image_from_geoportail)

    if veget_index_file and veget_index_file != "":
        print(f"Remplissage du champ Deviation à partir du fichier {veget_index_file}")
        pipeline |= pdal.Filter.colorization(raster=veget_index_file, dimensions="Deviation:1:256.0")
        writer_extra_dims = ["Deviation=ushort"]

    if color_rvb_enabled:
        tmp_ortho = tempfile.NamedTemporaryFile().name
        download_image_from_geoportail_retrying(proj, "ORTHOIMAGERY.ORTHOPHOTOS", minx, miny, maxx, maxy, pixel_per_meter, tmp_ortho, timeout_second)
        pipeline|= pdal.Filter.colorization(raster=tmp_ortho, dimensions="Red:1:256.0, Green:2:256.0, Blue:3:256.0")

    if color_ir_enabled:
        tmp_ortho_irc = tempfile.NamedTemporaryFile().name
        download_image_from_geoportail_retrying(proj, "ORTHOIMAGERY.ORTHOPHOTOS.IRC", minx, miny, maxx, maxy, pixel_per_meter, tmp_ortho_irc, timeout_second)
        pipeline |= pdal.Filter.colorization(raster=tmp_ortho_irc, dimensions="Infrared:1:256.0")

    pipeline |= pdal.Writer.las(filename=output_file, extra_dims=writer_extra_dims, minor_version="4", dataformat_id="8")

    print("Traitement du nuage de point")
    pipeline.execute()

    # os.remove(tmp_ortho)
    # os.remove(tmp_ortho_irc)


def parse_args():
    parser = argparse.ArgumentParser("Colorize tool")
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Input file")
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="",
        help="Output file")
    parser.add_argument(
        "--proj", "-p",
        type=str,
        default = "",
        help="Projection, default will use projection from metadata input")
    parser.add_argument(
        "--resolution", "-r",
        type=float,
        default = 5,
        help="Resolution, in pixel per meter")
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default = 300,
        help="Timeout, in seconds")
    parser.add_argument('--rvb', action='store_true', help="Colorize RVB")
    parser.add_argument('--ir', action='store_true', help="Colorize IR")
    parser.add_argument(
        "--vegetation",
        type=str,
        default = "",
        help="Vegetation file, value will be stored in Deviation field")
    return  parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    color(args.input, args.output, args.proj, args.resolution, args.timeout, args.rvb, args.ir, args.vegetation)