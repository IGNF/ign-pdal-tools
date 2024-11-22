import argparse
import logging
import os
import geopandas
import numpy as np
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
import rasterstats
from abc import ABC, abstractmethod


############################################## Actions #################################################################


class ActionOnGeo(ABC):

    # For now, action doesn't modify the geometry nature

    @abstractmethod
    def action_on_point(self, point, param) -> Point:
        pass

    def action_on_multipoint(self, multipoint, param) -> MultiPoint:
        return MultiPoint([self.action_on_point(pt, param) for pt in multipoint.geoms])

    @abstractmethod
    def action_on_linestring(self, line, param) -> LineString:
        pass

    def action_on_linearring(self, line, param) -> LineString:
        lline = LineString(line.coords)
        lline = self.action_on_linestring(lline, param)
        line = LinearRing(lline.coords)
        return line

    def action_on_multiline(self, mutilinestring, param) -> MultiLineString:
        return MultiLineString([self.action_on_linestring(ll, param) for ll in mutilinestring.geoms])

    def action_on_polygon(self, polygon, param) -> Polygon:
        exterior = self.action_on_linearring(polygon.exterior, param)
        interiors = [self.action_on_linearring(inter, param) for inter in polygon.interiors]
        return Polygon(exterior, interiors)

    def action_on_multipolygon(self, multipolygon, param) -> MultiPolygon:
        return MultiPolygon([self.action_on_polygon(pol, param) for pol in multipolygon.geoms])

    def action_on_geometrycollection(self, geometryCollection, param) -> GeometryCollection:
        return GeometryCollection([self.action_on_geometry(geo, param) for geo in geometryCollection.geoms])

    def action_on_geometry(self, geo, param):

        if geo.geom_type == "Point" or geo.geom_type == "MultiPoint":  # point : nothing to do
            return self.action_on_point(geo, param)

        if geo.geom_type == "LineString" or geo.geom_type == "LinearRing":
            return self.action_on_linestring(geo, param)

        if geo.geom_type == "MultiLineString":
            return self.action_on_multiline(geo, param)

        if geo.geom_type == "Polygon":
            return self.action_on_polygon(geo, param)

        if geo.geom_type == "MultiPolygon":
            return self.action_on_multipolygon(geo, param)

        if geo.geom_type == "GeometryCollection":
            return self.action_on_geometrycollection(geo, param)

    def apply_on_geometries(self, df, param):
        df["geometries"] = df.apply(lambda x: [self.action_on_geometry(g, param) for g in x], axis=1)
        df = (
            df.explode(column="geometries")
            .drop(columns="geometry")
            .set_geometry("geometries")
            .rename_geometry("geometry")
        )
        return df


############################################## concrete actions ########################################################


class Segmented(ActionOnGeo):
    def action_on_point(self, point, param):
        return point

    def action_on_linestring(self, line, param):
        distances = np.arange(0, line.length, param)
        points = [line.interpolate(distance) for distance in distances] + [line.boundary.geoms[1]]
        return LineString(points)


class AddZFromDTX(ActionOnGeo):
    def action_on_point(self, point, param):
        zz = rasterstats.point_query(point, param)
        return Point(point.x, point.y, zz[0])

    def action_on_linestring(self, line, param):
        zz = rasterstats.point_query(line, param)
        xx, yy = line.coords.xy
        points = [Point(xx[i], yy[i], zz[0][i]) for i in range(len(xx))]
        return LineString(points)


class AddVerticesIntersectionWithOtherGeo(ActionOnGeo):
    def action_on_point(self, point, param):
        return point

    def action_on_linestring(self, line, param):
        for geo in param:
            shared = line.intersection(geo)
            if shared:
                coords = [line.coords[i] for i in range(len(line.coords))] + [
                    shared.coords[i] for i in range(len(shared.coords))
                ]
                dists = [line.project(Point(p)) for p in coords]
                coords = [p for (d, p) in sorted(zip(dists, coords))]
                line = LineString(coords)
        return line


#################################################### Apply ############################################################


def transform_geo(input_geo: str, output_geo: str, interpol_raster: str, segmention: float, input_geo_snap):
    _, file_extension = os.path.splitext(output_geo)
    assert str.lower(file_extension) == ".json" or str.lower(file_extension) == ".geojson"

    file = open(input_geo)
    df = geopandas.read_file(file)

    # segment geometries
    if segmention > 0:
        df = Segmented().apply_on_geometries(df, segmention)

    # snap with other geometry
    if input_geo_snap is not None:
        file_snap = open(input_geo_snap)
        df_snap = geopandas.read_file(file_snap)
        df = AddVerticesIntersectionWithOtherGeo().apply_on_geometries(df, df_snap.geometry)

    # add Z from raster
    if interpol_raster is not None:
        df = AddZFromDTX().apply_on_geometries(df, interpol_raster)

    df.to_json()
    df.to_file(output_geo, driver="GeoJSON")


def parse_args():
    parser = argparse.ArgumentParser("Add points from geometry file in a las/laz file.")
    parser.add_argument("--input_geo", "-i", type=str, help="geometry input file")
    parser.add_argument("--output_geo", "-o", type=str, help="JSON output file.")
    parser.add_argument("--interpol_raster", "-r", type=str, help="Raster input file : Z are given on points.")
    parser.add_argument("--segmention", "-s", type=str, help="lenght of segmentation of each linestring.")
    parser.add_argument("--input_geo_snap", "-d", type=str, help="geometry input file for snap with input_geo.")
    return parser.parse_args()


def main():
    args = parse_args()
    transform_geo(
        input_geo=args.input_geo,
        interpol_raster=args.interpol_raster,
        output_geo=args.input_geo if args.output_geoe is None else args.output_geoe,
        segmention=args.segmention,
        input_geo_snap=args.input_geo_snap,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
