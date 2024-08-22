"""Tools to get information from a point cloud (points as a numpy array)"""

from typing import Tuple

import numpy as np


def get_pointcloud_origin_from_tile_width(
    points: np.ndarray, tile_width: int = 1000, buffer_size: float = 0
) -> Tuple[int, int]:
    """Get point cloud theoretical origin (xmin, ymax) for a data that originates from a square tesselation/tiling
    using the tesselation tile width only.

    Edge values are supposed to be included in the tile


    Args:
        points (np.ndarray): numpy array with the tile points
        tile_width (int, optional): Edge size of the square used for tiling. Defaults to 1000.
        buffer_size (float, optional): Optional buffer around the tile. Defaults to 0.

    Raises:
        ValueError: Raise an error when the bounding box of the tile is not included in a tile

    Returns:
        Tuple[int, int]: (origin_x, origin_y) origin coordinates
    """
    # Extract coordinates xmin, xmax, ymin and ymax of the original tile without buffer
    x_min, y_min = np.min(points[:, :2], axis=0) + buffer_size
    x_max, y_max = np.max(points[:, :2], axis=0) - buffer_size

    # Calculate the tiles to which x, y bounds belong
    tile_x_min = np.floor(x_min / tile_width)
    tile_x_max = np.floor(x_max / tile_width) if x_max % tile_width != 0 else np.floor(x_max / tile_width) - 1
    tile_y_min = np.ceil(y_min / tile_width) if y_min % tile_width != 0 else np.floor(y_min / tile_width) + 1
    tile_y_max = np.ceil(y_max / tile_width)

    if not (tile_x_max - tile_x_min) and not (tile_y_max - tile_y_min):
        origin_x = tile_x_min * tile_width
        origin_y = tile_y_max * tile_width
        return origin_x, origin_y
    else:
        raise ValueError(
            f"Min values (x={x_min} and y={y_min}) do not belong to the same theoretical tile as"
            f"max values (x={x_max} and y={y_max})."
        )
