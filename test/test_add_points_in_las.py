import pytest
import os
import random as rand
import tempfile
import math

import pdal

import geopandas as gpd
from shapely.geometry import Point

from pdaltools import add_points_in_las

numeric_precision = 4

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(TEST_PATH, "data")
INPUT_LAS = os.path.join(INPUT_DIR, "test_data_77055_627760_LA93_IGN69.laz")

Xmin = 770575
Ymin = 6277575
Zmin = 20
Size = 20

def distance3D(pt_geo, pt_las):
    return round(
        math.sqrt((pt_geo.x - pt_las['X']) ** 2 + (pt_geo.y - pt_las['Y']) ** 2 + (pt_geo.z - pt_las['Z']) ** 2),
        numeric_precision,
    )

def add_point_in_las(pt_geo, inside_las):
    geom = [pt_geo]
    series = gpd.GeoSeries(geom, crs="2154")

    with tempfile.NamedTemporaryFile(suffix="_geom_tmp.las") as out_las_file:
        with tempfile.NamedTemporaryFile(suffix="_geom_tmp.geojson") as geom_file:
            series.to_file(geom_file.name)

            added_dimensions = {"Classification":64, "Intensity":1.}
            add_points_in_las.add_points_in_las(INPUT_LAS, geom_file.name, out_las_file.name, inside_las, added_dimensions)

            pipeline = pdal.Pipeline() | pdal.Reader.las(out_las_file.name)
            pipeline.execute()
            points_las = pipeline.arrays[0]
            points_las = [e for e in points_las if all(e[val] == added_dimensions[val] for val in added_dimensions)]
            return points_las

def test_add_point_inside_las():
    X = Xmin + rand.uniform(0, 1) * Size
    Y = Ymin + rand.uniform(0, 1) * Size
    Z = Zmin + rand.uniform(0, 1) * 10
    pt_geo = Point(X, Y, Z)
    points_las = add_point_in_las(pt_geo=pt_geo, inside_las=True)
    assert len(points_las) == 1
    assert distance3D(pt_geo, points_las[0]) < 1 / numeric_precision

def test_add_point_outside_las_no_control():
    X = Xmin + rand.uniform(2, 3) * Size
    Y = Ymin + rand.uniform(0, 1) * Size
    Z = Zmin + rand.uniform(0, 1) * 10
    pt_geo = Point(X, Y, Z)
    points_las = add_point_in_las(pt_geo=pt_geo, inside_las=False)
    assert len(points_las) == 1
    assert distance3D(pt_geo, points_las[0]) < 1 / numeric_precision

def test_add_point_outside_las_with_control():
    X = Xmin + rand.uniform(2, 3) * Size
    Y = Ymin + rand.uniform(2, 3) * Size
    Z = Zmin + rand.uniform(0, 1) * 10
    pt_geo = Point(X, Y, Z)
    points_las = add_point_in_las(pt_geo=pt_geo, inside_las=True)
    assert len(points_las) == 0
