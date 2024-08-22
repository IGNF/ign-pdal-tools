"""Tools to get information from a point cloud (points as a numpy array)"""

from typing import Tuple

import numpy as np


def get_pointcloud_origin_from_tile_width(points: np.array, tile_width: int = 1000, buffer_size: float = 0) -> Tuple:
    """Get point cloud theoretical origin (xmin, ymax) for a data that originates from a square tesselation/tiling
    using the tesselation tile width only.

    Edge values are supposed to be included in the tile


    Args:
        points (np.array): numpy array with the tile points
        tile_width (int, optional): Edge size of the square used for tiling. Defaults to 1000.
        buffer_size (float, optional): Optional buffer around the tile. Defaults to 0.

    Raises:
        ValueError: Raise an error when the bounding box of the tile is not included in a tile

    Returns:
        Tuple: (origin_x, origin_y) origin coordinates
    """
    # Extract coordinates xmin, xmax, ymin and ymax of the original tile without buffer
    x_min, y_min = np.min(points[:, :2], axis=0) + buffer_size
    x_max, y_max = np.max(points[:, :2], axis=0) - buffer_size

    # Calculate the difference Xmin and Xmax, then Ymin and Ymax
    diff_tile_x = np.floor(x_max / tile_width) - np.floor(x_min / tile_width)
    is_x_max_on_edge = x_max % tile_width == 0
    diff_tile_y = np.ceil(y_max / tile_width) - np.ceil(y_min / tile_width)
    is_y_min_on_edge = y_min % tile_width == 0
    # Check [x_min - x_max] == amplitude and [y_min - y_max] == amplitude
    if (diff_tile_x == 0 or (diff_tile_x == 1 and is_x_max_on_edge)) and (
        diff_tile_y == 0 or (diff_tile_y == 1 and is_y_min_on_edge)
    ):
        origin_x = np.floor(x_min / tile_width) * tile_width  # round low
        origin_y = np.ceil(y_max / tile_width) * tile_width  # round top
        return origin_x, origin_y
    else:
        raise ValueError(
            f"Min values (x={x_min} and y={y_min}) do not belong to the same theoretical tile as"
            f"max values (x={x_max} and y={y_max})."
        )
