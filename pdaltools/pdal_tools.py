import json
import pdal
import logging


def las_info(filename: str, buffer_width: int=0, spatial_ref="EPSG:2154"):
    """ Get pdal infos using a pipeline that reads the whole dataset for extracting the bounding
    box from the LIDAR tile.
    Command "pdal_info --stats" does not seem to work properly on some data
    (TerraSolid output for ex)

    Args:
        filename (str): full path of file for which to get the bounding box
        border_width (str): number of pixel to add to the bounding box on each side (buffer size)

    Returns:
        bounds(tuple) : Tuple of bounding box from the LIDAR tile with potential buffer
    """
    # Parameters
    _x = []
    _y = []
    bounds= []
    information = {}
    information = {
    "pipeline": [
            {
                "type": "readers.las",
                "filename": filename,
                "override_srs": spatial_ref,
                "nosrs": True
            },
            {
                "type": "filters.info"
            }
        ]
    }

    # Create json
    json_info = json.dumps(information, sort_keys=True, indent=4)
    logging.info(json_info)
    pipeline = pdal.Pipeline(json_info)
    pipeline.execute()
    pipeline.arrays
    # Extract metadata
    metadata = pipeline.metadata
    if type(metadata) == str:
        metadata = json.loads(metadata)
    # Export bound (maxy, maxy, minx and miny), then creating a buffer with 100 m
    _x.append(float((metadata['metadata']['filters.info']['bbox']['minx']) - buffer_width)) # coordinate minX
    _x.append(float((metadata['metadata']['filters.info']['bbox']['maxx']) + buffer_width)) # coordinate maxX
    _y.append(float((metadata['metadata']['filters.info']['bbox']['miny']) - buffer_width)) # coordinate minY
    _y.append(float((metadata['metadata']['filters.info']['bbox']['maxy']) + buffer_width)) # coordinate maxY
    bounds.append(_x) # [xmin, xmax]
    bounds.append(_y) # insert [ymin, ymax]

    return tuple(i for i in bounds)
