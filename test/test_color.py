import os
import shutil
from pathlib import Path

import laspy
import numpy as np
import pytest

from pdaltools import color

cwd = os.getcwd()

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMPDIR = os.path.join(TEST_PATH, "tmp", "color")

INPUT_PATH = os.path.join(TEST_PATH, "data/test_noepsg_043500_629205_IGN69.laz")

OUTPUT_FILE = os.path.join(TMPDIR, "Semis_2021_0435_6292_LA93_IGN69.colorized.las")
EPSG = "2154"


def setup_module(module):
    try:
        shutil.rmtree(TMPDIR)
    except FileNotFoundError:
        pass
    os.mkdir(TMPDIR)


@pytest.mark.geopf
def test_epsg_fail():
    with pytest.raises(
        RuntimeError,
        match="EPSG could not be inferred from metadata: No 'srs' key in metadata.",
    ):
        color.color(INPUT_PATH, OUTPUT_FILE, "", 0.1, 15)


@pytest.mark.geopf
def test_color_and_keeping_orthoimages():
    tmp_ortho, tmp_ortho_irc = color.color(INPUT_PATH, OUTPUT_FILE, EPSG, check_images=True)
    assert Path(tmp_ortho.name).exists()
    assert Path(tmp_ortho_irc.name).exists()

    # TODO: Fix this test: it did not correspond to what was expected:
    # - GetNoDataValue returns the value of no_data, not the number of occurrences
    # - it is possible to have occasional no data values if no_data == 255. (white pixels)
    # for i in range(raster.RasterCount):
    #     assert raster.GetRasterBand(i + 1).GetNoDataValue() is None


@pytest.mark.parametrize(
    "minx, maxx, pixel_per_meter, expected_minx, expected_maxx",
    [(500, 1000, 5, 499.8, 1000.2), [1.1, 999.9, 5, 1, 1000]],
)
def test_match_min_max_with_pixel_size(minx, maxx, pixel_per_meter, expected_minx, expected_maxx):
    out_minx, out_maxx = color.match_min_max_with_pixel_size(minx, maxx, pixel_per_meter)
    assert (out_minx, out_maxx) == (expected_minx, expected_maxx)


@pytest.mark.geopf
def test_color_narrow_cloud():
    input_path = os.path.join(TEST_PATH, "data/test_data_0436_6384_LA93_IGN69_single_point.laz")
    output_path = os.path.join(TMPDIR, "color_narrow_cloud_test_data_0436_6384_LA93_IGN69_single_point.colorized.laz")
    # Test that clouds that are smaller in width or height to 20cm are still colorized without an error.
    color.color(input_path, output_path, EPSG)
    with laspy.open(output_path, "r") as las:
        las_data = las.read()
    # Check all points are colored
    assert not np.any(las_data.red == 0)
    assert not np.any(las_data.green == 0)
    assert not np.any(las_data.blue == 0)
    assert not np.any(las_data.nir == 0)


@pytest.mark.geopf
def test_color_standard_cloud():
    input_path = os.path.join(TEST_PATH, "data/test_data_77055_627760_LA93_IGN69.laz")
    output_path = os.path.join(TMPDIR, "color_standard_cloud_test_data_77055_627760_LA93_IGN69.colorized.laz")
    # Test that clouds that are smaller in width or height to 20cm are still colorized without an error.
    color.color(input_path, output_path, EPSG)
    with laspy.open(output_path, "r") as las:
        las_data = las.read()
    # Check all points are colored
    las_rgb_missing = (las_data.red == 0) & (las_data.green == 0) & (las_data.blue == 0)
    assert not np.any(las_rgb_missing), f"Should be no missing RGB value, got {np.count_nonzero(las_rgb_missing)} "
    assert not np.any(las_data.nir == 0)


@pytest.mark.geopf
def test_color_epsg_2975_forced():
    input_path = os.path.join(TEST_PATH, "data/sample_lareunion_epsg2975.laz")
    output_path = os.path.join(TMPDIR, "color_epsg_2975_forced_sample_lareunion_epsg2975.colorized.laz")

    color.color(input_path, output_path, 2975)


# the test is not working, the image is not detected as white
# certainly because of a fix on GPF side
# TODO: find a new area where the GPF returns a white image
# @pytest.mark.geopf
# def test_color_raise_for_white_image():
#    input_path = os.path.join(TEST_PATH, "data/sample_lareunion_epsg2975.laz")
#    output_path = os.path.join(TMPDIR, "sample_lareunion_epsg2975.colorized.white.laz")#

#    with pytest.raises(ValueError) as excinfo:
#        color.color(input_path, output_path, check_images=True)

#    assert "Downloaded image is white" in str(excinfo.value)


@pytest.mark.geopf
def test_color_epsg_2975_detected():
    input_path = os.path.join(TEST_PATH, "data/sample_lareunion_epsg2975.laz")
    output_path = os.path.join(TMPDIR, "color_epsg_2975_detected_sample_lareunion_epsg2975.colorized.laz")
    # Test that clouds that are smaller in width or height to 20cm are still clorized without an error.
    color.color(input_path, output_path)


def test_color_vegetation_only():
    """Test the color() function with only vegetation"""
    input_path = os.path.join(TEST_PATH, "data/test_data_77055_627760_LA93_IGN69.laz")
    output_path = os.path.join(TMPDIR, "test_color_vegetation.colorized.las")
    vegetation_path = os.path.join(TEST_PATH, "data/mock_vegetation.tif")

    # Test with all parameters explicitly defined
    color.color(
        input_file=input_path,
        output_file=output_path,
        proj="2154",  # EPSG:2154 (Lambert 93)
        color_rvb_enabled=False,  # RGB enabled
        color_ir_enabled=False,  # infrared enabled
        veget_index_file=vegetation_path,
        vegetation_dim="vegetation_dim",  # not default dimension name
    )

    # Verifications
    assert Path(output_path).exists(), "Output file should exist"

    # Verify the content of the colorized LAS file
    with laspy.open(output_path, "r") as las:
        las_data = las.read()

    # Verify that R, G, B, Infrared dimensions are not filled
    las_rgb_missing = (las_data.red == 0) & (las_data.green == 0) & (las_data.blue == 0)
    assert np.all(las_rgb_missing), "No point should have an RGB value"
    assert np.all(las_data.nir == 0), "No point should have NIR"

    # Verify that the vegetation dimension is present
    assert "vegetation_dim" in las_data.point_format.dimension_names, "Vegetation dimension should be present"
    assert not np.all(las_data.vegetation_dim == 0), "Vegetation dimension should not be empty"


@pytest.mark.geopf
def test_color_with_all_parameters():
    """Test the color() function with all parameters specified"""
    input_path = os.path.join(TEST_PATH, "data/test_data_77055_627760_LA93_IGN69.laz")
    output_path = os.path.join(TMPDIR, "test_color_all_params.colorized.las")
    vegetation_path = os.path.join(TEST_PATH, "data/mock_vegetation.tif")

    # Test with all parameters explicitly defined
    tmp_ortho, tmp_ortho_irc = color.color(
        input_file=input_path,
        output_file=output_path,
        proj="2154",  # EPSG:2154 (Lambert 93)
        pixel_per_meter=2.0,  # custom resolution
        timeout_second=120,  # custom timeout
        color_rvb_enabled=True,  # RGB enabled
        color_ir_enabled=True,  # infrared enabled
        veget_index_file=vegetation_path,
        vegetation_dim="vegetation_dim",  # not default dimension name
        check_images=True,  # image verification
        stream_RGB="ORTHOIMAGERY.ORTHOPHOTOS",  # default RGB stream
        stream_IRC="ORTHOIMAGERY.ORTHOPHOTOS.IRC",  # default IRC stream
        size_max_gpf=1000,  # custom GPF max size
    )

    # Verifications
    assert Path(output_path).exists(), "Output file should exist"

    # Verify that temporary images were created
    assert tmp_ortho is not None, "RGB ortho image should be created"
    assert tmp_ortho_irc is not None, "IRC ortho image should be created"
    assert Path(tmp_ortho.name).exists(), "RGB ortho temporary file should exist"
    assert Path(tmp_ortho_irc.name).exists(), "IRC ortho temporary file should exist"

    # Verify the content of the colorized LAS file
    with laspy.open(output_path, "r") as las:
        las_data = las.read()

    # Verify that all points have been colorized (no 0 values)
    las_rgb_missing = (las_data.red == 0) & (las_data.green == 0) & (las_data.blue == 0)
    assert not np.any(las_rgb_missing), f"No point should have missing RGB, found {np.count_nonzero(las_rgb_missing)}"
    assert not np.any(las_data.nir == 0), "No point should have missing NIR"

    # Verify that the vegetation dimension is present
    assert "vegetation_dim" in las_data.point_format.dimension_names, "Vegetation dimension should be present"
    assert not np.all(las_data.vegetation_dim == 0), "Vegetation dimension should not be empty"
