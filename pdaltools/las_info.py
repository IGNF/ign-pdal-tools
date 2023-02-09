import json
import pdal
import logging
import subprocess as sp


def las_info_metadata(filename: str):
    """Get las info from pdal info --metadata"""
    ret = sp.run(["pdal", "info", filename, "--metadata"], capture_output=True)
    if ret.returncode == 0:
        infos = ret.stdout.decode()
        infos = json.loads(infos)

        return infos['metadata']

    else:
        raise RuntimeError(f"pdal info failed with error: \n {ret.stderr}")


def las_info_pipeline(filename:str,  spatial_ref:str="EPSG:2154"):
    """Get las info from pdal pipeline with filter.info
    Args:
        filename: input las
        spatial_ref: spatial reference to pass as 'override_srs' argument in las reader
    """
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

    return metadata['metadata']['filters.info']


def las_get_xy_bounds(filename: str, buffer_width: int=0, spatial_ref:str="EPSG:2154"):
    """ Get tile bounds (xy only) from las metadata.
    Try getting bounds using las_info_metadata
    As command "pdal_info --metadata" does not seem to work properly on some data
    (TerraSolid output for ex), fallback to las_info_pipeline

    Args:
        filename (str): full path of file for which to get the bounding box
        border_width (str): number of pixel to add to the bounding box on each side (buffer size)
        spatial_ref: spatial reference to pass as 'override_srs' argument in las reader
        (Used if pdal info --metadata failed)

    Returns:
        bounds(tuple) : Tuple of bounding box from the LIDAR tile with potential buffer
    """
    # Parameters
    _x = []
    _y = []
    bounds= []
    try:
        metadata = las_info_metadata(filename)
        bounds_dict = metadata

    except RuntimeError as e:
        metadata = las_info_pipeline(filename, spatial_ref)
        bounds_dict = metadata["bbox"]
    if type(metadata) == str:
        metadata = json.loads(metadata)
    # Export bound (maxy, maxy, minx and miny), then creating a buffer with 100 m
    _x.append(float((bounds_dict['minx']) - buffer_width)) # coordinate minX
    _x.append(float((bounds_dict['maxx']) + buffer_width)) # coordinate maxX
    _y.append(float((bounds_dict['miny']) - buffer_width)) # coordinate minY
    _y.append(float((bounds_dict['maxy']) + buffer_width)) # coordinate maxY
    bounds.append(_x) # [xmin, xmax]
    bounds.append(_y) # insert [ymin, ymax]

    return tuple(i for i in bounds)
