""" Misc tools used in different tests
"""

import json
import subprocess as sp


def get_pdal_infos_summary(f: str):
    r = sp.run(["pdal", "info", "--summary", f], stderr=sp.PIPE, stdout=sp.PIPE)
    json_info = json.loads(r.stdout.decode())
    return json_info


EXPECTED_DIMS_BY_DATAFORMAT = {
    6: set(
        [
            "X",
            "Y",
            "Z",
            "Intensity",
            "ReturnNumber",
            "NumberOfReturns",
            "ScanChannel",
            "ScanDirectionFlag",
            "EdgeOfFlightLine",
            "Classification",
            "UserData",
            "ScanAngleRank",
            "PointSourceId",
            "GpsTime",
            "KeyPoint",
            "Overlap",
            "Synthetic",
            "Withheld",
        ]
    ),
    8: set(
        [
            "X",
            "Y",
            "Z",
            "Intensity",
            "ReturnNumber",
            "NumberOfReturns",
            "ScanChannel",
            "ScanDirectionFlag",
            "EdgeOfFlightLine",
            "Classification",
            "UserData",
            "ScanAngleRank",
            "PointSourceId",
            "GpsTime",
            "Red",
            "Green",
            "Blue",
            "Infrared",
            "KeyPoint",
            "Overlap",
            "Synthetic",
            "Withheld",
        ]
    ),
}
