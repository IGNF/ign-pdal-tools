"""Check if a LAS file is written correcty and can be opened by PDAL"""

import os
import shutil

import pytest

from pdaltools.check_las import (
    check_pdal_can_open_file,
    check_pdal_can_open_file_with_retry,
    check_pdal_can_open_file_with_retry_decorator,
)

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(TEST_PATH, "data/check_las")


def test_check_pdal_can_open_file():
    filepath = os.path.join(INPUT_DIR, "Semis_2022_0906_6665_LA93_IGN69_ok.laz")
    assert check_pdal_can_open_file(filepath)


def test_check_pdal_can_open_file_nok():
    filepath = os.path.join(INPUT_DIR, "Semis_2022_0906_6665_LA93_IGN69_nok.laz")
    assert not check_pdal_can_open_file(filepath)


def test_check_pdal_can_open_file_with_retry():
    filepath = os.path.join(INPUT_DIR, "Semis_2022_0906_6665_LA93_IGN69_ok.laz")
    assert check_pdal_can_open_file_with_retry(filepath, 1)


def test_check_pdal_can_open_file_with_retry_nok():
    filepath = os.path.join(INPUT_DIR, "Semis_2022_0906_6665_LA93_IGN69_nok.laz")
    assert not check_pdal_can_open_file_with_retry(filepath, 1)


@check_pdal_can_open_file_with_retry_decorator(delay=0, filepath="filepath")  # or mock time.sleep
def echo(filepath):
    return filepath


def test_decorator_passes_through_on_ok():
    filepath = os.path.join(INPUT_DIR, "Semis_2022_0906_6665_LA93_IGN69_ok.laz")
    assert echo(filepath) == filepath


def test_decorator_raises_on_nok():
    filepath = os.path.join(INPUT_DIR, "Semis_2022_0906_6665_LA93_IGN69_nok.laz")
    with pytest.raises(RuntimeError):
        echo(filepath)


@check_pdal_can_open_file_with_retry_decorator(delay=0, filepath="output_file")
def copy_las(input_file, output_file):
    shutil.copy(input_file, output_file)


def test_decorator_post_write_passes_on_ok(tmp_path):
    input_file = os.path.join(INPUT_DIR, "Semis_2022_0906_6665_LA93_IGN69_ok.laz")
    output_file = tmp_path / "output.laz"
    copy_las(input_file, output_file)
    print(output_file)
    assert output_file.is_file()


def test_decorator_post_write_raises_on_nok(tmp_path):
    input_file = os.path.join(INPUT_DIR, "Semis_2022_0906_6665_LA93_IGN69_nok.laz")
    output_file = tmp_path / "output.laz"
    with pytest.raises(RuntimeError):
        copy_las(input_file, output_file)
