""" Misc tools used in different tests
"""

import json
import subprocess as sp


def get_pdal_infos_summary(f: str):
    r = (sp.run(['pdal', 'info', '--summary', f], stderr=sp.PIPE, stdout=sp.PIPE))
    json_info = json.loads(r.stdout.decode())
    return json_info