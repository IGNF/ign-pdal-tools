import logging
import os

import pdal

from pdaltools.las_info import parse_filename


def create_filenames_suffixes(file: str, tile_width: int = 1000, tile_coord_scale: int = 1000):
    """Generate the name of the tiles around the input LIDAR tile
    It supposes that the file names are formatted as {prefix1}_{prefix2}_{coordx}_{coordy}_{suffix}
    with coordx and coordy having at least 4 digits

    For example Semis_2021_0000_1111_LA93_IGN69.las

    Generates only the suffix part of the filename, for example, for file like above, it will generate:
    _0000_1112_LA93_IGN69.las
    _0001_1112_LA93_IGN69.las
    ...

    Args:
        file(str): name of LIDAR file
        tile width (int): width of tiles in meters (usually 1000m)
        tile_coord_scale (int) : scale used in the filename to describe coordinates in meters
                (usually 1000m)
    Returns:
        list_input(list): List of LIDAR's filename suffix.
    """

    # Create name of LIDAR tiles who cercle the tile
    # # Parameters
    _prefix, coord_x, coord_y, _suffix = parse_filename(file)
    offset = int(tile_width / tile_coord_scale)
    # On left
    _tile_hl = f"_{(coord_x - offset):04d}_{(coord_y + offset):04d}_{_suffix}"
    _tile_ml = f"_{(coord_x - offset):04d}_{coord_y:04d}_{_suffix}"
    _tile_bl = f"_{(coord_x - offset):04d}_{(coord_y - offset):04d}_{_suffix}"
    # On Right
    _tile_hr = f"_{(coord_x + offset):04d}_{(coord_y + offset):04d}_{_suffix}"
    _tile_mr = f"_{(coord_x + offset):04d}_{coord_y:04d}_{_suffix}"
    _tile_br = f"_{(coord_x + offset):04d}_{(coord_y - offset):04d}_{_suffix}"
    # Above
    _tile_a = f"_{coord_x:04d}_{(coord_y + offset):04d}_{_suffix}"
    # Below
    _tile_b = f"_{coord_x:04d}_{(coord_y - offset):04d}_{_suffix}"
    # Return the severals tile's names
    return _tile_hl, _tile_ml, _tile_bl, _tile_a, _tile_b, _tile_hr, _tile_mr, _tile_br


def match_suffix_with_filenames(suffix_list: list, all_files: list, las_dir: str):
    """Match suffix list with real filenames
    Args:
        suffix_list (list): List of suffix patterns to match
        all_files (list): List of all files in las_dir
        las_dir (str): Directory of pointclouds

    Returns:
        las_list(List): List of matched files
    """
    las_list = []
    for suffix in suffix_list:
        matches = [filename for filename in all_files if filename.endswith(suffix)]
        if len(matches) == 0:
            logging.info(f"NOK : {suffix}")
        else:
            # in case of multiple matches, select the most recent year (ex: Semis_2021_ before Semis_2020_ )
            matches.sort(reverse=True)
            selected = matches[0]
            if len(matches) > 1:
                logging.warning(f"Multiple matches for {suffix} : {matches} ; taking {selected}")

            # Append full path
            las_list.append(os.path.join(las_dir, selected))
    return las_list


def create_tiles_list(all_files, las_dir, input_file, tile_width=1000, tile_coord_scale=1000):
    """Return the paths of 8 tiles around the tile + the input tile
    Args:
        all_files (list): list of all files in las_dir
        las_dir (str): directory of pointclouds
        input_file (str): path to queried LIDAR tile
        tile_width (int): Width of a tile(in the reference unit: 1m)
        tile_coord_scale (int): Scale used in filename to describe coordinates (usually kilometers)
        1000 * 1m (with 1m being the reference)

    Returns:
        list_files: list of tiles
    """

    # Return list 8 tiles around the tile, but only the suffix part of the name.
    suffix_list = create_filenames_suffixes(os.path.basename(input_file), tile_width, tile_coord_scale)

    # Match suffix patterns with real files
    list_files = match_suffix_with_filenames(suffix_list, all_files, las_dir)

    # Appending queried tile to list
    list_files.append(input_file)

    return list_files


def create_list(las_dir, input_file, tile_width=1000, tile_coord_scale=1000):
    """Return the paths of 8 tiles around the tile + the input tile
    Args:
        las_dir (str): directory of pointclouds
        input_file (str): path to queried LIDAR tile
        tile_width (int): Width of a tile(in the reference unit: 1m)
        tile_coord_scale (int): Scale used in filename to describe coordinates (usually kilometers)
        1000 * 1m (with 1m being the reference)

    Returns:
        list_files: list of tiles
    """

    # list files on the disk
    all_files = os.listdir(las_dir)

    # call the function with the list of files
    return create_tiles_list(all_files, las_dir, input_file, tile_width, tile_coord_scale)


def las_merge(las_dir, input_file, merge_file, tile_width=1000, tile_coord_scale=1000):
    """Merge LIDAR tiles around input_file tile
    Args:
        las_dir (str): directory of pointclouds (to look for neigboprs)
        input_file (str): name of query LIDAR file (with extension)
        output_file (str): path to output
        tile_width (int): Width of a tile(in the reference unit: 1m)
        tile_coord_scale (int): Scale used in filename to describe coordinates (usually kilometers)
        1000 * 1m (with 1m being the reference)
    """
    # List files to merge
    files = create_list(las_dir, input_file, tile_width, tile_coord_scale)
    if len(files) > 0:
        # Merge
        pipeline = pdal.Pipeline()
        for f in files:
            pipeline |= pdal.Reader.las(filename=f)
        pipeline |= pdal.Filter.merge()
        pipeline |= pdal.Writer.las(filename=merge_file, forward="all")
        pipeline.execute()
    else:
        raise ValueError("List of valid tiles is empty : stop processing")
