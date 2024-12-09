# Private helper methods
from typing import TextIO
from pathlib import Path


def process_file(file_or_filename) -> TextIO:
    """Return file-object if input is already a file.
    Otherwise, assume the argument is a path, and convert
    it to a new file-object.

    Note:
        The returned file-object is always in read-only mode.
    """

    # filename or path?
    if isinstance(file_or_filename, (str, Path)):
        return open(file_or_filename, "r")
    # file-like object?
    elif hasattr(file_or_filename, "read"):
        # if file-like object, force it to be opened read-only
        if file_or_filename.writable():
            filename = file_or_filename.name
            file_or_filename.close()  # FIXME: callers might get confused by suddenly closed files
            return open(filename, "r")
        else:
            return file_or_filename
    else:
        raise TypeError(
            f"Expected file object or str, but got value of type {type(file_or_filename)}"
        )
