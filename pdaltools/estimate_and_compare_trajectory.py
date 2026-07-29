"""
Compute an estimate of the sensor location based on the position of multiple returns and the sensor scan angle.
Then, ompares a computed trajectory against a reference trajectory and alerts on large Z gaps.

"""
import argparse
import json
from pathlib import Path

import numpy as np
import pdal


def compute_trajectory_from_returns(las_files: list[Path], fid: str) -> np.ndarray:
    """Computes an estimate of the sensor location based on the position of multiple returns and the sensor scan angle.

    Also writes the computed trajectory to `trajectoire_bande_{fid}.csv` as a side effect.

    Args:
        las_files (list[Path]): LAS/LAZ files to read.
        fid (str): `PointSourceId` values corresponding to the trajectory number.

    Returns:
        np.ndarray: Structured array of the computed trajectory points, with fields
            `GpsTime`, `X`, `Y`, `Z`.
    """
    pipeline = pdal.Pipeline(
        json.dumps(
            [
                *(str(f) for f in las_files),
                {"type": "filters.merge"},
                {"type": "filters.range", "limits": f"PointSourceId[{fid}:{fid}]"},
                {"type": "filters.sort", "dimension": "GpsTime"},
                {"type": "filters.trajectory", "dtr": 0.002, "minsep": 0.5, "tblock": 1.0, "tout": 0.01},
                {
                    "type": "writers.text",
                    "filename": f"trajectoire_bande_{fid}.csv",
                    "format": "csv",
                    "order": "GpsTime,X,Y,Z",
                },
            ]
        )
    )
    pipeline.execute()
    print(f"Bande {fid} -> trajectoire_bande_{fid}.csv")
    return pipeline.arrays[0]


def compare_trajectories(computed: np.ndarray, reference_trajectory: Path, dz_threshold: float = 40.0) -> None:
    """Compares a computed trajectory against a reference trajectory and alerts on large Z gaps.

    Args:
        computed (np.ndarray): Structured array with fields `GpsTime`, `X`, `Y`, `Z`, as returned by
            `compute_trajectory_from_returns`.
        reference_trajectory (Path): Reference trajectory file (GeoJSON), with a `timestamp`
            and `z` property per point.
        dz_threshold (float): Alert threshold in meters for `|Z_ref - Z_computed|`. Default 40.

    Returns:
        None
    """
    with open(reference_trajectory) as f:
        features = json.load(f)["features"]
    ref_time, ref_z = (
        np.array(values, dtype=np.float64)
        for values in zip(*((p["timestamp"], p["z"]) for p in (feat["properties"] for feat in features)))
    )
    # np.interp requires xp (ref_time) sorted ascending -- hence the argsort above.
    sort_idx = np.argsort(ref_time)
    ref_time, ref_z = ref_time[sort_idx], ref_z[sort_idx]

    computed_time = computed["GpsTime"].astype(np.float64)
    computed_z = computed["Z"].astype(np.float64)

    # The two trajectories are rarely sampled at the same GpsTime, so linear
    # interpolation reconstructs Z_ref at each computed timestamp before diffing.
    # NB: outside [ref_time.min(), ref_time.max()], np.interp clamps to the
    # nearest edge value instead of extrapolating -- dz will look artificially
    # flat there if computed_time runs past the reference trajectory's window.
    z_ref_interp = np.interp(computed_time, ref_time, ref_z)
    abs_dz = np.abs(z_ref_interp - computed_z)

    n_alerts = int(np.count_nonzero(abs_dz > dz_threshold))
    if n_alerts:
        print(
            f"ALERTE : {n_alerts}/{len(abs_dz)} points avec |Z_traj - Z_recalcule| > {dz_threshold} m "
            f"(ecart max = {abs_dz.max():.1f} m)"
        )
    else:
        print(f"OK : ecart max |Z_traj - Z_recalcule| = {abs_dz.max():.1f} m (seuil {dz_threshold} m)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Computes an estimate of the sensor location based on the position of multiple returns "
        "and the sensor scan angle, and optionally compares it against a reference trajectory."
    )
    parser.add_argument("las_files", nargs="+", type=Path, default=None, help="LAS/LAZ files to read.")
    parser.add_argument(
        "PointSourceId", type=str, default=None, help="`PointSourceId` values corresponding to the trajectory number"
    )
    parser.add_argument(
        "--reference-trajectory",
        type=Path,
        default=None,
        help="Reference trajectory GeoJSON file to compare the computed trajectory against.",
    )
    parser.add_argument(
        "--dz-threshold",
        type=float,
        default=40.0,
        help="Alert threshold in meters for |Z_ref - Z_computed| (default: 40).",
    )
    args = parser.parse_args()

    missing = [f for f in args.las_files if not f.is_file()]
    if missing:
        parser.error(f"file(s) not found: {', '.join(str(f) for f in missing)}")
    if args.reference_trajectory is not None and not args.reference_trajectory.is_file():
        parser.error(f"reference trajectory not found: {args.reference_trajectory}")

    computed_trajectory = compute_trajectory_from_returns(args.las_files, args.PointSourceId)

    if args.reference_trajectory is not None:
        compare_trajectories(computed_trajectory, args.reference_trajectory, args.dz_threshold)
