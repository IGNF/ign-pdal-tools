"""Tools to get information from a point cloud (points as a numpy array)"""

from typing import Tuple

import numpy as np


def infer_tile_origin(minx: float, maxx: float, miny: float, maxy: float, tile_width: int) -> Tuple[int, int]:
    """Get point cloud theoretical origin (xmin, ymax) for a data that originates from a square tesselation/tiling
    using the tesselation tile width only, based on the min/max values

    Edge values are supposed to be included in the tile

    Args:
        minx (float): point cloud min x value
        maxx (float): point cloud max x value
        miny (float): point cloud min y value
        maxy (float): point cloud max y value
        tile_width (int): tile width in meters

    Raises:
        ValueError: In case the min and max values do not belong to the same tile

    Returns:
        Tuple[int, int]: (origin_x, origin_y) tile origin coordinates = theoretical (xmin, ymax)
    """

    minx_tile_index = np.floor(minx / tile_width)
    maxx_tile_index = np.floor(maxx / tile_width) if maxx % tile_width != 0 else np.floor(maxx / tile_width) - 1
    miny_tile_index = np.ceil(miny / tile_width) if miny % tile_width != 0 else np.floor(miny / tile_width) + 1
    maxy_tile_index = np.ceil(maxy / tile_width)

    if maxx_tile_index == minx_tile_index and maxy_tile_index == miny_tile_index:
        origin_x = minx_tile_index * tile_width
        origin_y = maxy_tile_index * tile_width
        return origin_x, origin_y
    else:
        raise ValueError(
            f"Min values (x={minx} and y={miny}) do not belong to the same theoretical tile as"
            f"max values (x={maxx} and y={maxy})."
        )


def get_pointcloud_origin_from_tile_width(
    points: np.ndarray, tile_width: int = 1000, buffer_size: float = 0
) -> Tuple[int, int]:
    """Get point cloud theoretical origin (xmin, ymax) for a data that originates from a square tesselation/tiling
    using the tesselation tile width only, based on the point cloud as a np.ndarray

    Edge values are supposed to be included in the tile

    In case buffer_size is provided, the origin will be calculated on an "original" tile, supposing that
    there has been a buffer added to the input tile.

    Args:
        points (np.ndarray): numpy array with the tile points
        tile_width (int, optional): Edge size of the square used for tiling. Defaults to 1000.
        buffer_size (float, optional): Optional buffer around the tile. Defaults to 0.

    Raises:
        ValueError: Raise an error when the initial tile is smaller than the buffer (in this case, we cannot find the
        origin (it can be either in the buffer or in the tile))

    Returns:
        Tuple[int, int]: (origin_x, origin_y) origin coordinates
    """
    # Extract coordinates xmin, xmax, ymin and ymax of the original tile without buffer
    minx, miny = np.min(points[:, :2], axis=0) + buffer_size
    maxx, maxy = np.max(points[:, :2], axis=0) - buffer_size

    if maxx < minx or maxy < miny:
        raise ValueError(
            "Cannot find pointcloud origin as the pointcloud width or height is smaller than buffer width"
        )

    return infer_tile_origin(minx, maxx, miny, maxy, tile_width)
