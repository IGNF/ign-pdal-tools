import laspy
import os
import shutil

from pdaltools import color


TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMPDIR = os.path.join(TEST_PATH, "tmp")

def setup_module(module):
    try:
        shutil.rmtree(TMPDIR)
    except (FileNotFoundError):
        pass
    os.mkdir(TMPDIR)


def test_copy_and_hack_decorator():
    # bug during laz opening in pdal (solved with copy_and_hack_decorator)
    LAZ_FILE = os.path.join(TEST_PATH, 'data/test_pdalfail_0643_6319_LA93_IGN69.laz')
    LAS_FILE = os.path.join(TMPDIR, "test_pdalfail_0643_6319_LA93_IGN69.las")

    color.decomp_and_color(LAZ_FILE, LAS_FILE, "", 1)

    las = laspy.read(LAS_FILE)
    print(las.header)
    print(list(las.point_format.dimension_names))
    print(las.red)
    print(las.green)
    print(las.blue)
    print(las.nir)

    assert os.path.isfile(LAS_FILE)