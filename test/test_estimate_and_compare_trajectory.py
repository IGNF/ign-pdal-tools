"""Test computing a trajectory estimate from LAS returns and comparing it to a reference trajectory"""

import json
import os
import shutil
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import pytest

from pdaltools.estimate_and_compare_trajectory import (
    compare_trajectories,
    compute_trajectory_from_returns,
)

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(TEST_PATH, "data/estimate_and_compare_trajectory")
OUTPUT_DIR = os.path.join(TEST_PATH, "tmp/estimate_and_compare_trajectory")

LAS_FILES = [
    Path(INPUT_DIR) / "Semis_2021_0490_6518_LA93_IGN69_clip.laz",
    Path(INPUT_DIR) / "Semis_2021_0490_6519_LA93_IGN69_clip.laz",
]
MISSING_LAS_FILES = [Path(INPUT_DIR) / "does_not_exist.laz", LAS_FILES[1]]
REFERENCE_TRAJECTORY = Path(INPUT_DIR) / "test_20210930_181334_20_axe_15.json"
MISSING_REFERENCE_TRAJECTORY = Path(INPUT_DIR) / "does_not_exist.json"
FID = "15"
MISSING_FID = "999"  # PointSourceId absent from LAS_FILES


def setup_module(module):
    try:
        shutil.rmtree(OUTPUT_DIR)
    except FileNotFoundError:
        pass
    os.makedirs(OUTPUT_DIR)


@pytest.mark.parametrize(
    "las_files, fid, reference_trajectory, expectation",
    [
        pytest.param(LAS_FILES, FID, REFERENCE_TRAJECTORY, nullcontext(), id="ok"),
        pytest.param(
            LAS_FILES,
            MISSING_FID,
            REFERENCE_TRAJECTORY,
            pytest.raises(ValueError, match="No returns found"),
            id="missing_pointsourceid",
        ),
        pytest.param(
            MISSING_LAS_FILES,
            FID,
            REFERENCE_TRAJECTORY,
            pytest.raises(RuntimeError, match="Unable to open stream"),
            id="missing_laz",
        ),
        pytest.param(
            LAS_FILES,
            FID,
            MISSING_REFERENCE_TRAJECTORY,
            pytest.raises(FileNotFoundError),
            id="missing_trajectory",
        ),
    ],
)
def test_estimate_and_compare_trajectory(las_files, fid, reference_trajectory, expectation):
    with expectation:
        computed = compute_trajectory_from_returns(las_files, fid, output_dir=OUTPUT_DIR)

        assert {"GpsTime", "X", "Y", "Z"}.issubset(computed.dtype.names)
        assert len(computed) > 0
        # `compute_trajectory_from_returns` also writes the trajectory to a CSV as a side effect
        assert (Path(OUTPUT_DIR) / f"trajectoire_bande_{fid}.csv").is_file()

        compare_trajectories(computed, reference_trajectory)


def test_compute_trajectory_from_returns_writes_csv_to_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # cwd != output_dir, to prove the CSV follows output_dir, not cwd
    output_dir = tmp_path / "trajectories"
    output_dir.mkdir()

    computed = compute_trajectory_from_returns(LAS_FILES, FID, output_dir=output_dir)

    assert {"GpsTime", "X", "Y", "Z"}.issubset(computed.dtype.names)
    assert len(computed) > 0
    assert (output_dir / f"trajectoire_bande_{FID}.csv").is_file()
    assert not (tmp_path / f"trajectoire_bande_{FID}.csv").is_file()


def test_compare_trajectories_alerts_on_z_gap(capsys):
    """Uses a small synthetic dataset (not real lidar returns) built specifically to force a Z gap alert."""
    computed = np.array(
        [(317060880.0, 490500.0, 6518000.0, 2000.0), (317060881.0, 490500.0, 6518000.0, 2000.0)],
        dtype=[("GpsTime", "f8"), ("X", "f8"), ("Y", "f8"), ("Z", "f8")],
    )
    reference_trajectory = Path(OUTPUT_DIR) / "synthetic_reference_trajectory.json"
    reference_trajectory.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [490500.0, 6518000.0]},
                        "properties": {"timestamp": 317060880.0, "z": 500.0},
                    },
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [490500.0, 6518000.0]},
                        "properties": {"timestamp": 317060881.0, "z": 500.0},
                    },
                ],
            }
        )
    )

    ok = compare_trajectories(computed, reference_trajectory)  # default dz_threshold=40.0, actual gap = 1500m

    assert ok is False
    out = capsys.readouterr().out
    assert "ALERTE" in out
    assert f"{len(computed)}/{len(computed)}" in out
