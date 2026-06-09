"""Check that LAS/LAZ files can be read by PDAL.

Provides a one-shot check, a retry variant (for files still being written), and a
decorator that validates an output path after a wrapped function returns.
"""

import functools
import inspect
import os
import time

import pdal


def check_pdal_can_open_file(filepath: str) -> bool:
    try:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File {filepath} does not exist.")
        pipeline = pdal.Reader.las(filename=filepath).pipeline()
        pipeline.execute()
        return True
    except RuntimeError as e:
        if e.__str__().startswith("readers.las:"):
            print(f"Pdal could not read {filepath} due to error: {e}")
            return False
        else:
            raise e


def check_pdal_can_open_file_with_retry(filepath: str, delay: int) -> bool:
    if check_pdal_can_open_file(filepath):
        return True
    else:
        print(f"New attempt in {delay} seconds.")
        time.sleep(delay)
        return check_pdal_can_open_file(filepath)


def check_pdal_can_open_file_with_retry_decorator(delay: int, filepath: str | None = None):
    def decorator(fn):
        sig = inspect.signature(fn)

        # Extract the LAS path from the wrapped call: bind args/kwargs to the
        # function signature, apply defaults if needed, then return the parameter
        # named by `filepath` (e.g. "output_file" or the first positional arg).
        def resolve_filepath(*args, **kwargs) -> str:
            bound = sig.bind_partial(*args, **kwargs)
            if filepath not in bound.arguments:
                bound.apply_defaults()
            return str(bound.arguments[filepath])

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            resolved_filepath = resolve_filepath(*args, **kwargs)
            if not check_pdal_can_open_file_with_retry(resolved_filepath, delay):
                raise RuntimeError(f"Pdal could not read {resolved_filepath} after retry.")
            return result

        return wrapper

    return decorator
