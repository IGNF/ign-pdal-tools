import os
import sys
import tempfile

import laspy
import numpy as np
import pdal
import pytest

from pdaltools import las_add_extra_dims_from_las

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(TEST_PATH, "data")
INI_LAS = os.path.join(INPUT_DIR, "test_data_77055_627760_LA93_IGN69.laz")
ADDED_DIMS = ["DIM_1", "DIM_2"]


def _las_dim_attr(dimension_name: str) -> str:
    return {"X": "x", "Y": "y", "Z": "z"}.get(dimension_name, dimension_name)


def _append_extra_dims(input_las: str, output_las: str) -> None:
    pipeline = pdal.Pipeline()
    pipeline |= pdal.Reader.las(input_las)
    pipeline |= pdal.Filter.ferry(dimensions="=>" + ", =>".join(ADDED_DIMS))
    pipeline |= pdal.Writer.las(output_las, extra_dims="all", forward="all")
    pipeline.execute()


def _pdal_first_array(las_path: str):
    p = pdal.Pipeline() | pdal.Reader.las(las_path)
    p.execute()
    return p.arrays[0]


def _assert_base_dimensions_unchanged(base: laspy.LasData, out: laspy.LasData) -> None:
    assert len(out) == len(base)
    for name in base.point_format.dimension_names:
        attr = _las_dim_attr(name)
        b = np.asarray(getattr(base, attr))
        o = np.asarray(getattr(out, attr))
        if np.issubdtype(b.dtype, np.floating):
            np.testing.assert_allclose(b, o, rtol=0, atol=1e-3, err_msg=name)
        else:
            np.testing.assert_array_equal(b, o, err_msg=name)


def test_add_extra_dims():
    """Test that adding all extra dimensions works."""
    with tempfile.NamedTemporaryFile(suffix="_with_extra.las", delete_on_close=False) as tmp_src:
        _append_extra_dims(INI_LAS, tmp_src.name)
        with tempfile.NamedTemporaryFile(suffix="_merged.las", delete_on_close=False) as tmp_out:
            las_add_extra_dims_from_las.add_extra_dims_from_las(
                base_las=INI_LAS,
                source_las=tmp_src.name,
                output_las=tmp_out.name,
            )
            arr_base = _pdal_first_array(INI_LAS)
            arr_src = _pdal_first_array(tmp_src.name)
            arr_out = _pdal_first_array(tmp_out.name)
            n_base = arr_base.shape[0]
            assert arr_src.shape[0] == n_base == arr_out.shape[0]
            names_src = set(arr_src.dtype.names)
            names_out = set(arr_out.dtype.names)
            assert ADDED_DIMS[0] in names_out and ADDED_DIMS[1] in names_out
            for d in ADDED_DIMS:
                assert d in names_src
                np.testing.assert_array_equal(arr_src[d], arr_out[d])


def test_add_subset_dimensions():
    """Test that adding a subset of dimensions works."""
    with tempfile.NamedTemporaryFile(suffix="_with_extra.las", delete_on_close=False) as tmp_src:
        _append_extra_dims(INI_LAS, tmp_src.name)
        with tempfile.NamedTemporaryFile(suffix="_merged.las", delete_on_close=False) as tmp_out:
            las_add_extra_dims_from_las.add_extra_dims_from_las(
                base_las=INI_LAS,
                source_las=tmp_src.name,
                output_las=tmp_out.name,
                dimensions=["DIM_1"],
            )
            n_base = _pdal_first_array(INI_LAS).shape[0]
            arr_out = _pdal_first_array(tmp_out.name)
            assert arr_out.shape[0] == n_base
            names_out = set(arr_out.dtype.names)
            assert "DIM_1" in names_out
            assert "DIM_2" not in names_out


def test_point_count_unchanged_after_merge():
    """Output and source point counts match the base file."""
    with tempfile.NamedTemporaryFile(suffix="_with_extra.las", delete_on_close=False) as tmp_src:
        _append_extra_dims(INI_LAS, tmp_src.name)
        with tempfile.NamedTemporaryFile(suffix="_merged.las", delete_on_close=False) as tmp_out:
            n_base = len(laspy.read(INI_LAS))
            las_add_extra_dims_from_las.add_extra_dims_from_las(
                base_las=INI_LAS,
                source_las=tmp_src.name,
                output_las=tmp_out.name,
            )
            assert len(laspy.read(tmp_src.name)) == n_base
            assert len(laspy.read(tmp_out.name)) == n_base


def test_existing_standard_dimensions_unchanged_after_merge():
    """Every dimension from the base file (INI_LAS) is unchanged in the output; only DIM_1 is added."""
    with tempfile.NamedTemporaryFile(suffix="_with_extra.las", delete_on_close=False) as tmp_src:
        _append_extra_dims(INI_LAS, tmp_src.name)
        with tempfile.NamedTemporaryFile(suffix="_merged.las", delete_on_close=False) as tmp_out:
            las_add_extra_dims_from_las.add_extra_dims_from_las(
                base_las=INI_LAS,
                source_las=tmp_src.name,
                output_las=tmp_out.name,
                dimensions=["DIM_1"],
            )

            base = laspy.read(INI_LAS)
            out = laspy.read(tmp_out.name)
            _assert_base_dimensions_unchanged(base, out)
            arr_src = _pdal_first_array(tmp_src.name)
            arr_out = _pdal_first_array(tmp_out.name)
            np.testing.assert_array_equal(arr_src["DIM_1"], arr_out["DIM_1"])


def test_output_las_version_follows_base_not_source():
    """Output LAS major/minor must match the base file even when the donor declares another version."""
    n = 3
    x = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    y = np.zeros(n, dtype=np.float64)
    z = np.zeros(n, dtype=np.float64)
    gps = np.array([0.0, 0.1, 0.2], dtype=np.float64)

    for base_ver, src_ver in (("1.2", "1.4"), ("1.4", "1.2")):
        with tempfile.NamedTemporaryFile(suffix="_base.las", delete_on_close=False) as fbase:
            with tempfile.NamedTemporaryFile(suffix="_src.las", delete_on_close=False) as fsrc:
                with tempfile.NamedTemporaryFile(suffix="_out.las", delete_on_close=False) as fout:
                    base = laspy.create(point_format=3, file_version=base_ver)
                    base.x, base.y, base.z, base.gps_time = x, y, z, gps
                    base.write(fbase.name)
                    base_hdr = laspy.read(fbase.name).header

                    src = laspy.create(point_format=3, file_version=src_ver)
                    src.x, src.y, src.z, src.gps_time = x, y, z, gps
                    src.add_extra_dim(laspy.ExtraBytesParams(name="pred", type=np.float32))
                    src.pred[:] = np.array([1.0, 2.0, 3.0], dtype=np.float32)
                    src.write(fsrc.name)

                    las_add_extra_dims_from_las.add_extra_dims_from_las(
                        fbase.name,
                        fsrc.name,
                        fout.name,
                        dimensions=["pred"],
                    )
                    out_hdr = laspy.read(fout.name).header
                    assert str(out_hdr.version) == str(base_hdr.version), (
                        f"expected output LAS version {base_hdr.version}, got {out_hdr.version} "
                        f"(base {base_ver}, source {src_ver})"
                    )


def test_missing_gps_time_in_base_raises():
    """GPS time is required in the base file."""
    with tempfile.NamedTemporaryFile(suffix="_base.las", delete_on_close=False) as fbase:
        with tempfile.NamedTemporaryFile(suffix="_src.las", delete_on_close=False) as fsrc:
            with tempfile.NamedTemporaryFile(suffix="_out.las", delete_on_close=False) as fout:
                base = laspy.create(point_format=0, file_version="1.2")
                base.x = [0.0]
                base.y = [0.0]
                base.z = [0.0]
                base.write(fbase.name)

                src = laspy.create(point_format=3, file_version="1.4")
                src.x = [0.0]
                src.y = [0.0]
                src.z = [0.0]
                src.gps_time = [1.0]
                src.add_extra_dim(laspy.ExtraBytesParams(name="extra_f", type=np.float32))
                src.extra_f = np.array([1.0], dtype=np.float32)
                src.write(fsrc.name)

                with pytest.raises(ValueError, match="gps_time"):
                    las_add_extra_dims_from_las.add_extra_dims_from_las(fbase.name, fsrc.name, fout.name)


def test_point_count_mismatch_raises():
    """The base and source files must have the same number of points."""
    with tempfile.NamedTemporaryFile(suffix="_a.las", delete_on_close=False) as fa:
        with tempfile.NamedTemporaryFile(suffix="_b.las", delete_on_close=False) as fb:
            la = laspy.create(point_format=3, file_version="1.4")
            la.x = [0, 1]
            la.y = [0, 0]
            la.z = [0, 0]
            la.write(fa.name)
            lb = laspy.create(point_format=3, file_version="1.4")
            lb.x = [0]
            lb.y = [0]
            lb.z = [0]
            lb.add_extra_dim(laspy.ExtraBytesParams(name="only_in_b", type=np.float32))
            lb.only_in_b = np.array([1.0], dtype=np.float32)
            lb.write(fb.name)
            with tempfile.NamedTemporaryFile(suffix="_o.las", delete_on_close=False) as fo:
                with pytest.raises(ValueError, match="Point count mismatch"):
                    las_add_extra_dims_from_las.add_extra_dims_from_las(fa.name, fb.name, fo.name)


def test_shuffled_row_order_xyz_alignment():
    """The base and source files may have different row order."""
    n = 20
    rng = np.random.default_rng(42)
    x = rng.random(n) * 100
    y = rng.random(n) * 100
    z = rng.random(n) * 10
    gps = np.arange(n, dtype=np.float64)
    pred = rng.random(n).astype(np.float32)

    perm = rng.permutation(n)

    with tempfile.NamedTemporaryFile(suffix="_base.las", delete_on_close=False) as fbase:
        with tempfile.NamedTemporaryFile(suffix="_src.las", delete_on_close=False) as fsrc:
            with tempfile.NamedTemporaryFile(suffix="_out.las", delete_on_close=False) as fout:
                base = laspy.create(point_format=3, file_version="1.4")
                base.x = x
                base.y = y
                base.z = z
                base.gps_time = gps
                base.write(fbase.name)

                src = laspy.create(point_format=3, file_version="1.4")
                src.x = x[perm]
                src.y = y[perm]
                src.z = z[perm]
                src.gps_time = gps[perm]
                src.add_extra_dim(laspy.ExtraBytesParams(name="pred", type=np.float32))
                src.pred = pred[perm]
                src.write(fsrc.name)

                las_add_extra_dims_from_las.add_extra_dims_from_las(
                    fbase.name,
                    fsrc.name,
                    fout.name,
                    dimensions=["pred"],
                )
                out = laspy.read(fout.name)
                np.testing.assert_allclose(np.asarray(out.pred), pred, rtol=0, atol=1e-6)


def test_batch_directories_common_basenames(tmp_path):
    """Test that adding extra dimensions works for a batch of files."""
    base_dir = tmp_path / "base"
    src_dir = tmp_path / "src"
    out_dir = tmp_path / "out"
    base_dir.mkdir()
    src_dir.mkdir()

    n = 6
    rng = np.random.default_rng(0)
    x = rng.random(n) * 10
    y = rng.random(n) * 10
    z = rng.random(n) * 10
    gps = np.arange(n, dtype=np.float64)
    pred = rng.random(n).astype(np.float32)

    for fname in ("a.las", "b.las"):
        base = laspy.create(point_format=3, file_version="1.4")
        base.x = x
        base.y = y
        base.z = z
        base.gps_time = gps
        base.write(str(base_dir / fname))

        src = laspy.create(point_format=3, file_version="1.4")
        src.x = x
        src.y = y
        src.z = z
        src.gps_time = gps
        src.add_extra_dim(laspy.ExtraBytesParams(name="extra_dim", type=np.float32))
        src.extra_dim = pred
        src.write(str(src_dir / fname))

    only_base = laspy.create(point_format=3, file_version="1.4")
    only_base.x = [0.0]
    only_base.y = [0.0]
    only_base.z = [0.0]
    only_base.gps_time = [0.0]
    only_base.write(str(base_dir / "only_base.las"))

    done = las_add_extra_dims_from_las.add_extra_dims_from_las_dirs(base_dir, src_dir, out_dir)
    assert set(done) == {"a.las", "b.las"}

    for fname in ("a.las", "b.las"):
        merged = laspy.read(out_dir / fname)
        np.testing.assert_allclose(np.asarray(merged.extra_dim), pred, rtol=0, atol=1e-6)


def test_batch_no_common_filenames_raises(tmp_path):
    """No common filenames between the base and source directories."""
    base_dir = tmp_path / "base"
    src_dir = tmp_path / "src"
    out_dir = tmp_path / "out"
    base_dir.mkdir()
    src_dir.mkdir()
    out_dir.mkdir()

    b = laspy.create(point_format=3, file_version="1.4")
    b.x = [0.0]
    b.y = [0.0]
    b.z = [0.0]
    b.gps_time = [1.0]
    b.write(str(base_dir / "a.las"))

    s = laspy.create(point_format=3, file_version="1.4")
    s.x = [0.0]
    s.y = [0.0]
    s.z = [0.0]
    s.gps_time = [1.0]
    s.add_extra_dim(laspy.ExtraBytesParams(name="e", type=np.float32))
    s.e = np.array([1.0], dtype=np.float32)
    s.write(str(src_dir / "other.las"))

    with pytest.raises(ValueError, match="No common LAS"):
        las_add_extra_dims_from_las.add_extra_dims_from_las_dirs(base_dir, src_dir, out_dir)


def test_main_cli_single_file_merge(monkeypatch):
    """CLI entrypoint: ``main()`` parses argv and merges one base/source/output file triple."""
    with tempfile.NamedTemporaryFile(suffix="_with_extra.las", delete_on_close=False) as tmp_src:
        _append_extra_dims(INI_LAS, tmp_src.name)
        with tempfile.NamedTemporaryFile(suffix="_merged.las", delete_on_close=False) as tmp_out:
            monkeypatch.setattr(
                sys,
                "argv",
                [
                    "las_add_extra_dims_from_las",
                    "--base",
                    INI_LAS,
                    "--source",
                    tmp_src.name,
                    "--output",
                    tmp_out.name,
                    "--dimensions",
                    "DIM_1",
                ],
            )
            las_add_extra_dims_from_las.main()
            assert os.path.getsize(tmp_out.name) > 0
            n_ini = len(laspy.read(INI_LAS))
            arr_out = _pdal_first_array(tmp_out.name)
            assert arr_out.shape[0] == n_ini
            assert "DIM_1" in arr_out.dtype.names
            assert "DIM_2" not in arr_out.dtype.names


def test_main_cli_mixed_file_and_directory_exits(monkeypatch, tmp_path):
    """CLI rejects --base directory with --source file (must be both files or both directories)."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    lone = laspy.create(point_format=3, file_version="1.4")
    lone.x = [0.0]
    lone.y = [0.0]
    lone.z = [0.0]
    lone.gps_time = [0.0]
    lone_las = tmp_path / "only.las"
    lone.write(str(lone_las))

    out_las = tmp_path / "out.las"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "las_add_extra_dims_from_las",
            "--base",
            str(base_dir),
            "--source",
            str(lone_las),
            "--output",
            str(out_las),
        ],
    )
    with pytest.raises(SystemExit, match="both be files or both be directories"):
        las_add_extra_dims_from_las.main()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
