import pytest
import os
import random as rand
import tempfile

import pdal

import geopandas as gpd
from shapely.geometry import Polygon, Point

from pdaltools import add_points_in_las



TEST_PATH = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(TEST_PATH, "data")
INPUT_LAS = os.path.join(INPUT_DIR, "test_data_77055_627760_LA93_IGN69.laz")

Xmin = 770550
Ymin = 6277552
Zmin = 20
Size = 50

def build_random_point():
    X = Xmin + rand.uniform(0, 1) * Size
    Y = Ymin + rand.uniform(0, 1) * Size
    Z = Zmin + rand.uniform(0, 1) * 10
    return Point(X, Y, Z)

def build_random_geom(nb_geom : int, out_geom_file: str):

    geom=[]

    # add some points
    for i in range(nb_geom):
        geom.append(build_random_point())

    # add some polygon:
    for i in range(nb_geom):
        coordinates = []
        for i in range(4+nb_geom):
            coordinates.append(build_random_point())
        polygon = Polygon(coordinates)
        geom.append(polygon)

    series = gpd.GeoSeries(geom, crs="2154")
    series.to_file(out_geom_file)

    # return the number of points
    return nb_geom + nb_geom*(4+nb_geom+1)

@pytest.mark.parametrize("execution_number", range(3))
def test_extract_points_from_geo(execution_number):

    with tempfile.NamedTemporaryFile(suffix="_geom_tmp.geojson") as geom_file:
        nb_points_to_extract = build_random_geom(rand.randint(5,20), geom_file.name)
        points = add_points_in_las.extract_points_from_geo(geom_file.name)
        assert nb_points_to_extract == len(points)


def get_nb_points_from_las(input_las: str, dict_conditions = {}):
    pipeline = pdal.Pipeline() | pdal.Reader.las(input_las)
    pipeline.execute()
    if not dict_conditions:
        return len(pipeline.arrays[0])
    return len([e for e in pipeline.arrays[0] if all(e[val] == dict_conditions[val] for val in dict_conditions)])


@pytest.mark.parametrize("execution_number", range(3))
def test_add_points_in_las(execution_number):

    with tempfile.NamedTemporaryFile(suffix="_geom_tmp.las") as out_las_file:
        with tempfile.NamedTemporaryFile(suffix="_geom_tmp.geojson") as geom_file:
            nb_points_to_extract = build_random_geom(rand.randint(3, 10), geom_file.name)
            added_dimensions = {"Classification":64, "Intensity":1.}
            add_points_in_las.add_points_in_las(INPUT_LAS, geom_file.name, out_las_file.name, added_dimensions)
            nb_points_ini = get_nb_points_from_las(INPUT_LAS)
            nb_points_to_find = nb_points_ini + nb_points_to_extract
            nb_points_end = get_nb_points_from_las(out_las_file.name)
            nb_points_end_class = get_nb_points_from_las(out_las_file.name, added_dimensions)
            assert nb_points_end == nb_points_to_find
            assert nb_points_end_class == nb_points_to_extract


