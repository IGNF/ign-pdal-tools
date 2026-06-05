import json
import os
import shutil
import sys
from unittest.mock import patch

import laspy
import numpy as np
import pytest

from pdaltools.count_occurences.count_occurences_for_attribute import compute_count_one_file
from pdaltools.las_comparison import compare_las_dimensions
from pdaltools.run_pdal_pipeline import bind_input_output, load_pipeline_json, main, run_pdal_pipeline

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp")
INPUT_DIR = os.path.join(TEST_PATH, "data", "classified_laz")
INPUT_LAZ = os.path.join(INPUT_DIR, "test_data_77050_627755_LA93_IGN69.laz")
PIPELINE_JSON = os.path.join(TEST_PATH, "data", "example_pdal_pipeline.json")
PIPELINE_WITH_IO_JSON = os.path.join(TEST_PATH, "data", "example_pdal_pipeline_with_io.json")
PIPELINE_MULTI_FILTERS_JSON = os.path.join(TEST_PATH, "data", "example_pdal_pipeline_multi_filters.json")
OUTPUT_LAZ = os.path.join(TMP_PATH, "run_pdal_pipeline_out.laz")
OUTPUT_WITH_IO_LAZ = os.path.join(TMP_PATH, "run_pdal_pipeline_with_io_out.laz")
OUTPUT_MULTI_FILTERS_LAZ = os.path.join(TMP_PATH, "run_pdal_pipeline_multi_filters_out.laz")
OUTPUT_RECLASS_LAZ = os.path.join(TMP_PATH, "run_pdal_pipeline_reclass.laz")

MULTI_FILTER_STAGES = [
    {"type": "filters.expression", "expression": "Z > 30"},
    {"type": "filters.assign", "value": "Classification = 13 WHERE Classification == 5"},
]

Z_THRESHOLD = 30.0


def _las_point_count(filepath: str) -> int:
    with laspy.open(filepath) as las:
        return las.header.point_count


def _count_points_by_z(filepath: str, *, z_gt_threshold: bool, threshold: float = Z_THRESHOLD) -> int:
    with laspy.open(filepath) as las:
        points = las.read().points
        z = np.asarray(points.z)
    if z_gt_threshold:
        return int(np.sum(z > threshold))
    return int(np.sum(z <= threshold))


def _count_points_by_class(filepath: str, class_id: int) -> int:
    with laspy.open(filepath) as las:
        points = las.read().points
        classification = np.asarray(points.classification)
        return int(np.sum((classification) == class_id))

def _count_classification_with_z_gt(
    filepath: str,
    class_id: int,
    z_gt_threshold: bool = True,
    threshold: float = Z_THRESHOLD,
) -> int:
    """Count points matching classification == class_id and Z relative to threshold."""
    with laspy.open(filepath) as las:
        points = las.read().points
        z = np.asarray(points.z)
        classification = np.asarray(points.classification)
    z_mask = z > threshold if z_gt_threshold else z <= threshold
    return int(np.sum((classification == class_id) & z_mask))

def setup_module(module):
    try:
        shutil.rmtree(TMP_PATH)
    except FileNotFoundError:
        pass
    os.makedirs(TMP_PATH, exist_ok=True)


def test_load_pipeline_json_from_string():
    stages = load_pipeline_json('[{"type": "filters.expression", "expression": "Z>0"}]')
    assert stages == [{"type": "filters.expression", "expression": "Z>0"}]


def test_load_pipeline_json_from_file(tmp_path):
    path = tmp_path / "pipeline.json"
    path.write_text('[{"type": "filters.range", "limits": "Classification[0:255]"}]')
    assert load_pipeline_json(str(path)) == [
        {"type": "filters.range", "limits": "Classification[0:255]"}
    ]


def test_load_pipeline_json_from_repo_fixture():
    stages = load_pipeline_json(PIPELINE_JSON)
    assert stages == [{"type": "filters.range", "limits": "Classification[0:255]"}]


def test_load_pipeline_json_rejects_invalid():
# test load_pipeline_json with invalid input
# pdal pipeline is a json array of objects with a type key
    with pytest.raises(ValueError, match="empty"):
        load_pipeline_json("   ")
    with pytest.raises(ValueError, match="JSON"):
        load_pipeline_json("{not json")
    with pytest.raises(ValueError, match="array"):
        load_pipeline_json('{"type": "readers.las"}')
    with pytest.raises(ValueError, match="type"):
        load_pipeline_json('[{"nope": 1}]')


def test_bind_input_output_wraps_filters():
    bound = bind_input_output(
        [{"type": "filters.expression", "expression": "Z>0"}],
        "in.laz",
        "out.laz",
    )
    assert bound[0] == {"type": "readers.las", "filename": "in.laz"}
    assert bound[-1] == {"type": "writers.las", "filename": "out.laz", "extra_dims": "all", "forward": "all"}


def test_bind_input_output_patches_reader_and_writer():
    bound = bind_input_output(
        [
            {"type": "readers.las", "filename": "old_in.laz"},
            {"type": "filters.range", "limits": "Classification[0:255]"},
            {"type": "writers.las", "filename": "old_out.laz", "extra_dims": "all", "forward": "all"},
        ],
        "new_in.laz",
        "new_out.laz",
    )

    assert bound[0] == {"type": "readers.las", "filename": "new_in.laz"}
    assert bound[1] == {"type": "filters.range", "limits": "Classification[0:255]"}
    assert bound[2] == {"type": "writers.las", "filename": "new_out.laz", "extra_dims": "all", "forward": "all"}


def test_bind_input_output_rejects_invalid_reader_and_writer():
    with pytest.raises(ValueError, match="readers.las"):
        bind_input_output(
            [{"type": "readers.xyz", "filename": "old_in.laz"},
            {"type": "filters.range", "limits": "Classification[0:255]"},
            {"type": "writers.las", "filename": "old_out.laz", "extra_dims": "all", "forward": "all"},
        ],
        "new_in.laz",
        "new_out.laz",
    )
    with pytest.raises(ValueError, match="writers.las"):
        bind_input_output(
            [{"type": "readers.las", "filename": "old_in.laz"},
            {"type": "filters.range", "limits": "Classification[0:255]"},
            {"type": "writers.xyz", "filename": "old_out.laz", "extra_dims": "all", "forward": "all"},
        ],
        "new_in.laz",
        "new_out.laz",
    )

@patch("pdaltools.run_pdal_pipeline.run_pdal_pipeline")
def test_main_cli(mock_run):
    
    sys.argv = [
        "run_pdal_pipeline",
        "--input_file",
        INPUT_LAZ,
        "--output_file",
        OUTPUT_LAZ,
        "--pipeline",
        PIPELINE_JSON,
    ]
    main()

    mock_run.assert_called_once_with(
        INPUT_LAZ,
        OUTPUT_LAZ,
        [{"type": "filters.range", "limits": "Classification[0:255]"}],
    )


def test_run_pdal_pipeline_integration_preserves_point_count():
    run_pdal_pipeline(INPUT_LAZ, OUTPUT_LAZ, load_pipeline_json(PIPELINE_JSON))
    assert os.path.isfile(OUTPUT_LAZ)
    assert os.path.getsize(OUTPUT_LAZ) > 0

    # Check if the output file is identical to the input file (the pipeline should not change the point count)
    identical, nb_diff, percentage = compare_las_dimensions(INPUT_LAZ, OUTPUT_LAZ)
    assert identical, f"OUTPUT_LAZ differs from INPUT_LAZ ({nb_diff} points, {percentage}% diff)"
    assert nb_diff == 0, f"OUTPUT_LAZ differs from INPUT_LAZ ({nb_diff} points, {percentage}% diff)"
    assert percentage == 0, f"OUTPUT_LAZ differs from INPUT_LAZ ({nb_diff} points, {percentage}% diff)"


def test_run_bind_input_output_with_embedded_reader_and_writer():
    """Pipeline JSON already defines readers.las and writers.las; CLI paths must replace them."""
    stages = load_pipeline_json(PIPELINE_WITH_IO_JSON)
    
    bound = bind_input_output(stages, INPUT_LAZ, OUTPUT_WITH_IO_LAZ)
    assert len(bound) == 3
    assert bound[0] == {"type": "readers.las", "filename": INPUT_LAZ}
    assert bound[-1]["type"] == "writers.las"
    assert bound[-1]["filename"] == OUTPUT_WITH_IO_LAZ
    assert bound[-1]["extra_dims"] == "all"
    assert bound[-1]["forward"] == "major_version" # not the default value "all"
    assert bound[1] == {"type": "filters.range", "limits": "Classification[0:255]"}


def test_run_pdal_pipeline_with_embedded_reader_and_writer():
    """Pipeline JSON already defines readers.las and writers.las; CLI paths must replace them."""
    stages = load_pipeline_json(PIPELINE_WITH_IO_JSON)    
    run_pdal_pipeline(INPUT_LAZ, OUTPUT_WITH_IO_LAZ, stages)
    assert os.path.isfile(OUTPUT_WITH_IO_LAZ)

    _, nb_diff, percentage = compare_las_dimensions(INPUT_LAZ, OUTPUT_WITH_IO_LAZ)
    assert nb_diff == 0, f"output differs from input ({nb_diff} points)"
    assert percentage == 0 , f"output differs from input {percentage}% diff)"
    

def test_bind_input_output_with_several_filters():
    stages = load_pipeline_json(PIPELINE_MULTI_FILTERS_JSON)
    assert stages == MULTI_FILTER_STAGES
    assert all(stage["type"].startswith("filters.") for stage in stages)

    bound = bind_input_output(stages, INPUT_LAZ, OUTPUT_MULTI_FILTERS_LAZ)
    assert len(bound) == 4
    assert bound[1:-1] == MULTI_FILTER_STAGES


def test_run_pdal_pipeline_with_several_filters():
    """Chained filters.expression (Z > 30) and filters.assign (class 5 -> 13)."""

    source_class = 5
    target_class = 13

    stages = load_pipeline_json(PIPELINE_MULTI_FILTERS_JSON)
    run_pdal_pipeline(INPUT_LAZ, OUTPUT_MULTI_FILTERS_LAZ, stages)
    assert os.path.isfile(OUTPUT_MULTI_FILTERS_LAZ)

    n_input_points = _las_point_count(INPUT_LAZ)
    n_input_z_le_30 = _count_points_by_z(INPUT_LAZ, z_gt_threshold=False)
    n_input_z_gt_30 = _count_points_by_z(INPUT_LAZ, z_gt_threshold=True)
    
    assert n_input_points > 0
    assert n_input_points == n_input_z_le_30 + n_input_z_gt_30
    assert n_input_z_gt_30 > 0, "fixture must contain points with Z > 30"

    #number of points in source with (Z>30 & class==5)
    n_source = _count_classification_with_z_gt(INPUT_LAZ, source_class)
    assert n_source > 0, f"fixture must contain classification {source_class} with Z > 30"

    #keep only points z>30 in output
    n_output_points = _las_point_count(OUTPUT_MULTI_FILTERS_LAZ)
    assert n_output_points == n_input_z_gt_30

    #no more points with z<=30
    n_output_z_le_30 = _count_points_by_z(OUTPUT_MULTI_FILTERS_LAZ, z_gt_threshold=False)
    assert n_output_z_le_30==0

    #no more points of class==5
    output_counts = compute_count_one_file(OUTPUT_MULTI_FILTERS_LAZ)
    assert int(output_counts.get(str(source_class), 0)) == 0
    
    #number of points in target with (Z>30 & class==13)
    n_target_in_z_gt = _count_classification_with_z_gt(OUTPUT_MULTI_FILTERS_LAZ, target_class)

    #number of points in target with (Z>30 & class==13) == 0
    n_target_in_z_le = _count_classification_with_z_gt(OUTPUT_MULTI_FILTERS_LAZ, target_class, False)
    assert n_target_in_z_le == 0

    #number of points in target with class==13
    n_target_class = _count_points_by_class(OUTPUT_MULTI_FILTERS_LAZ, target_class)
    assert n_target_class == n_target_in_z_gt
    assert n_target_class == n_source
    assert sum(int(v) for v in output_counts.values()) == n_output_points