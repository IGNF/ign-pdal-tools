import json
import os
import pdal
import logging


def create_filenames(file: str):
    """Generate the name of the tiles around the input LIDAR tile

    Args:
        _file(str): name of LIDAR file
    Returns:
        _Listinput(list): List of LIDAR's name
    """
    _file = os.path.basename(file)  # Make sure that we work on the base name and not the full path

    elements = _file.split("_", 4)
    # Create name of LIDAR tiles who cercle the tile
    # # Parameters
    _prefix = f"{elements[0]}_{elements[1]}"
    _suffix = elements[-1]
    coord_x = int(elements[2])
    coord_y = int(elements[3])
    # On left
    _tile_hl = f"{_prefix}_{(coord_x - 1):04d}_{(coord_y + 1):04d}_{_suffix}"
    _tile_ml = f"{_prefix}_{(coord_x - 1):04d}_{coord_y:04d}_{_suffix}"
    _tile_bl = f"{_prefix}_{(coord_x - 1):04d}_{(coord_y - 1):04d}_{_suffix}"
    # On Right
    _tile_hr = f"{_prefix}_{(coord_x + 1):04d}_{(coord_y + 1):04d}_{_suffix}"
    _tile_mr = f"{_prefix}_{(coord_x + 1):04d}_{coord_y:04d}_{_suffix}"
    _tile_br = f"{_prefix}_{(coord_x + 1):04d}_{(coord_y - 1):04d}_{_suffix}"
    # Above
    _tile_a = f"{_prefix}_{coord_x:04d}_{(coord_y + 1):04d}_{_suffix}"
    # Below
    _tile_b = f"{_prefix}_{coord_x:04d}_{(coord_y - 1):04d}_{_suffix}"
    # Return the severals tile's names
    return _tile_hl, _tile_ml, _tile_bl, _tile_a, _tile_b, _tile_hr, _tile_mr, _tile_br


def check_tiles_exist(list_las: list):
    """ Check if pointclouds exist
    Args:
        list_las (list): Filenames of the tiles around the LIDAR tile

    Returns:
        li(List): Pruned list of filenames with only existing files
    """
    li = []
    for i in list_las:
        if not os.path.exists(i):
            logging.info(f'NOK : {i}')
            pass
        else:
            li.append(i)
    return li


def create_list(las_dir, input_file):
    """Return the paths of 8 tiles around the tile + the input tile
    Args:
        las_dir (str): directory of pointclouds
        input_file (str): path to queried LIDAR tile

    Returns:
        Listfiles(li): list of tiles
    """

    # Return list 8 tiles around the tile
    Listinput = create_filenames(os.path.basename(input_file))
    # List pointclouds
    li = [os.path.join(las_dir, e) for e in Listinput]
    # Keep only existing files
    li = check_tiles_exist(li)
    # Appending queried tile to list
    li.append(input_file)

    return li


def las_merge(las_dir, input_file, merge_file):
    """Merge LIDAR tiles around input_file tile
    Args:
        las_dir (str): directory of pointclouds (to look for neigboprs)
        input_file (str): name of query LIDAR file (with extension)
        output_file (str): path to output
    """
    # List files to merge
    Listfiles = create_list(las_dir, input_file)
    if len(Listfiles) > 0:
        # Merge
        information = {}
        information = {
                "pipeline":
                        Listfiles + [merge_file]
        }
        merge = json.dumps(information, sort_keys=True, indent=4)
        logging.info(merge)
        pipeline = pdal.Pipeline(merge)
        pipeline.execute()
    else:
        raise ValueError('List of valid tiles is empty : stop processing')
