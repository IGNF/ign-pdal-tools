import pytest
import os
from pdaltools import transform_geo

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(TEST_PATH, "data")
INPUT_GEO = os.path.join(INPUT_DIR, "test_segment.geojson")
INPUT_GEO_SNAP = os.path.join(INPUT_DIR, "test_segment_snap.geojson")
INPUT_INTERPOL_DTM = os.path.join(INPUT_DIR, "Crop.tif")

from shapely.geometry import (
    LineString,
    Point,
    Polygon,
    MultiPolygon,
    MultiPoint,
    MultiLineString,
    GeometryCollection,
    LinearRing,
)

########################### Test apply on geometry #######################


def test_on_point():
    pt = Point(837739, 6434524)
    pt = transform_geo.AddZFromDTX().action_on_point(pt, INPUT_INTERPOL_DTM)
    assert pt.z > 0


def test_on_multipoint():
    mpt = MultiPoint([[837739, 6434524], [837739, 6434525]])
    mpt = transform_geo.AddZFromDTX().action_on_multipoint(mpt, INPUT_INTERPOL_DTM)
    assert len(mpt.geoms) == 2
    assert mpt.geoms[0].z > 0
    assert mpt.geoms[1].z > 0


def test_on_linestring():
    line = LineString([[837739, 6434524], [837739, 6434525]])
    line = transform_geo.AddZFromDTX().action_on_linestring(line, INPUT_INTERPOL_DTM)
    assert len(line.coords) == 2
    assert line.coords[0][2] > 0
    assert line.coords[1][2] > 0


def test_on_multiline():
    mline = MultiLineString([[[837739, 6434524], [837739, 6434525]], [[837740, 6434525], [837739, 6434524]]])
    mline = transform_geo.AddZFromDTX().action_on_multiline(mline, INPUT_INTERPOL_DTM)
    assert len(mline.geoms) == 2
    assert len(mline.geoms[0].coords) == 2
    assert mline.geoms[0].coords[0][2] > 0


def test_on_linearring():
    ring = LinearRing(((837739, 6434524), (837739, 6434525), (837740, 6434525), (837739, 6434524)))
    ring = transform_geo.AddZFromDTX().action_on_linearring(ring, INPUT_INTERPOL_DTM)
    assert len(ring.coords) == 4
    assert ring.coords[0][2] > 0
    assert ring.coords[1][2] > 0


def test_on_polygon():
    poly = Polygon(((837739, 6434524), (837739, 6434525), (837740, 6434525), (837739, 6434524)))
    poly = transform_geo.AddZFromDTX().action_on_polygon(poly, INPUT_INTERPOL_DTM)
    assert len(poly.exterior.coords) == 4
    for pt in poly.exterior.coords:
        assert pt[2] > 0


def test_on_polygon_with_hole():
    poly = Polygon(
        ((837739, 6434524), (837739, 6434525), (837740, 6434525), (837739, 6434524)),
        [((837739.5, 6434524.5), (837739.5, 6434524.75), (837739.75, 6434524.75), (837739.5, 6434524.5))],
    )
    poly = transform_geo.AddZFromDTX().action_on_polygon(poly, INPUT_INTERPOL_DTM)
    assert len(poly.exterior.coords) == 4
    assert len(poly.interiors) == 1
    assert len(poly.interiors[0].coords) == 4
    for pt in poly.interiors[0].coords:
        assert pt[2] > 0


def test_on_multipolygon():
    mpoly = MultiPolygon(
        [
            (
                ((837739, 6434524), (837739, 6434525), (837740, 6434525), (837739, 6434524)),
                [((837739.5, 6434524.5), (837739.5, 6434524.75), (837739.75, 6434524.75), (837739.5, 6434524.5))],
            ),
            (
                ((837739, 6434524), (837739, 6434525), (837740, 6434525), (837739, 6434524)),
                [((837739.5, 6434524.5), (837739.5, 6434524.75), (837739.75, 6434524.75), (837739.5, 6434524.5))],
            ),
        ]
    )
    mpoly = transform_geo.AddZFromDTX().action_on_multipolygon(mpoly, INPUT_INTERPOL_DTM)
    assert len(mpoly.geoms) == 2
    assert mpoly.geoms[0].exterior.coords[0][2] > 0


def test_on_geometrycollection():
    pt = Point(837739, 6434524)
    line = LineString([[837739, 6434524], [837739, 6434525]])
    poly = Polygon(((837739, 6434524), (837739, 6434525), (837740, 6434525), (837739, 6434524)))
    gc = GeometryCollection([pt, line, poly])
    gc = transform_geo.AddZFromDTX().action_on_geometrycollection(gc, INPUT_INTERPOL_DTM)
    assert len(gc.geoms) == 3
    assert gc.geoms[0].z > 0
    assert gc.geoms[1].coords[0][2] > 0
    assert gc.geoms[2].exterior.coords[0][2] > 0


########################## Test functions #######################


def test_segment():
    line = LineString([[837739, 6434524], [837739, 6434525]])
    distance_segment = 0.25
    line = transform_geo.Segmented().action_on_linestring(line, distance_segment)
    assert len(line.coords) == 5


def test_addVerticesIntersectionWithOtherGeo():
    line = LineString([[837738, 6434524.5], [837740, 6434524.5]])
    line_snap = LineString([[837739, 6434524], [837739, 6434525]])
    geometries_snap = [line_snap]
    line = transform_geo.AddVerticesIntersectionWithOtherGeo().action_on_linestring(line, geometries_snap)
    assert len(line.coords) == 3


def test_addZFromDTX():
    pt = Point(837739, 6434524)
    pt = transform_geo.AddZFromDTX().action_on_point(pt, INPUT_INTERPOL_DTM)
    assert abs(pt.z - 339.7) < 0.2  # 339.7 is a value determine by hand


########################## Test main #######################
def test_apply_main():
    output_geo_test = os.path.join(INPUT_DIR, "test_segment_out.geojson")
    transform_geo.transform_geo(INPUT_GEO, output_geo_test, INPUT_INTERPOL_DTM, 0.25, INPUT_GEO_SNAP)
    assert os.path.isfile(INPUT_GEO)
