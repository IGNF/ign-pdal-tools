import argparse
from pdaltools.las_merge import create_list
from pdaltools.las_info import get_buffered_bounds_from_filename

import logging
import os
import pdal
from typing import List


def create_las_with_buffer(input_dir: str, tile_filename: str,
                           output_filename: str,
                           buffer_width: int=100,
                           spatial_ref: str="EPSG:2154",
                           tile_width: int=1000,
                           tile_coord_scale: int=1000):
    """Merge lidar tiles around the queried tile and crop them in order to add a buffer
    to the tile (usually 100m).
    Args:
        input_dir (str): directory of pointclouds (where you look for neigbors)
        tile_filename (str): full path to the queried LIDAR tile
        output_filename (str) : full path to the saved cropped tile
        buffer_width (int): width of the border to add to the tile (in pixels)
        spatial_ref (str): Spatial reference to use to override the one from input las.
        tile width (int): width of tiles in meters (usually 1000m)
        tile_coord_scale (int) : scale used in the filename to describe coordinates in meters
                (usually 1000m)
    """
    bounds = get_buffered_bounds_from_filename(tile_filename, buffer_width=buffer_width,
                                               tile_width=tile_width,
                                               tile_coord_scale=tile_coord_scale)

    logging.debug(f"Add buffer of size {buffer_width} to tile.")
    las_merge_and_crop(input_dir, tile_filename, bounds, output_filename, spatial_ref,
                       tile_width=tile_width, tile_coord_scale=tile_coord_scale)


def las_merge_and_crop(input_dir: str, tile_filename: str, bounds: List,
        output_filename: str, spatial_ref: str="EPSG:2154",
        tile_width=1000, tile_coord_scale=1000):
    """ Merge and crop las in a single pipeline (for buffer addition)

    For performance reasons, instead of using a pipeline that reads all files, merge them and
    then crop to the desired bbox, what is done is:
    - For each file:
        - read it
        - crop it according to the bounds
        - keep the crop in memory
        - delete the pipeline object to release the memory taken by the las reader
    - Merge the already cropped data

    Args:
        input_dir (str): directory of pointclouds (where you look for neigbors)
        tile_filename (str): full path to the queried LIDAR tile
        bounds : 2D bounding box to crop to : provided as ([xmin, xmax], [ymin, ymax])
        output_filename (str) : full path to the saved cropped tile
        spatial_ref (str): spatial reference for the writer
        tile width (int): width of tiles in meters (usually 1000m)
        tile_coord_scale (int) : scale used in the filename to describe coordinates in meters
                (usually 1000m)
    """
    # List files to merge
    Listfiles = create_list(input_dir, tile_filename, tile_width, tile_coord_scale)

    if len(Listfiles) > 0:
        # Read and crop each file
        crops = []
        for f in Listfiles:
            pipeline = pdal.Pipeline()
            pipeline |= pdal.Reader.las(filename=f, override_srs=spatial_ref)
            pipeline |= pdal.Filter.crop(bounds=str(bounds))
            pipeline.execute()
            if len(pipeline.arrays[0]) == 0:
                logging.warning(f"File {f} ignored in merge/crop: No points in crop bounding box")
            else:
                crops.append(pipeline.arrays[0])

            del pipeline

        # Merge
        pipeline = pdal.Filter.merge().pipeline(*crops)

        # Write
        pipeline |= pdal.Writer(filename=output_filename, a_srs=spatial_ref)

        logging.info(pipeline.toJSON())
        pipeline.execute()
    else:
        raise ValueError('List of valid tiles is empty : stop processing')
    pass


def parse_args():
    parser = argparse.ArgumentParser("Add a buffer to a las tile by stitching with its neighbors")
    parser.add_argument(
        "--input_dir", "-i",
        type=str,
        required=True,
        help="Path to the the folder containing the tile to which you want to add buffer"+
             "as well as its neighbors tiles")
    parser.add_argument(
        "--tile_filename", "-f",
        type=str,
        required=True,
        help="Filename of the input tile (basename only)")
    parser.add_argument(
        "--output_dir", "-o",
        type=str,
        required=True,
        help="Directory folder for saving the outputs")
    parser.add_argument(
        "--buffer_width", "-b",
        default=100,
        type=int,
        help="Width (in meter) for the buffer that is added to the tile before interpolation " +
             "(to prevent artefacts)"
    )
    # Optional parameters
    parser.add_argument(
        "--spatial_reference",
        default="EPSG:2154",
        help="Spatial reference to use to override the one from input las."
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    create_las_with_buffer(input_dir=args.input_dir,
                           tile_filename=os.path.join(args.input_dir, args.tile_filename),
                           output_filename=os.path.join(args.output_dir, args.tile_filename),
                           buffer_width=args.buffer_width,
                           spatial_ref=args.spatial_reference)
