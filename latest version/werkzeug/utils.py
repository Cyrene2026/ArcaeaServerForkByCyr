import os
import re
import unicodedata


_filename_ascii_strip_re = re.compile(r"[^A-Za-z0-9_.-]")


def secure_filename(filename: str) -> str:
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")
    filename = filename.replace(os.path.sep, " ")
    if os.path.altsep:
        filename = filename.replace(os.path.altsep, " ")
    filename = "_".join(filename.split())
    filename = _filename_ascii_strip_re.sub("", filename).strip("._")
    return filename or "file"
