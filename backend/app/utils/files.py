import re


def secure_filename(filename: str) -> str:
    """Strip path separators and unsafe characters from a filename."""
    if not filename:
        return "file"
    filename = filename.replace("\\", "/").split("/")[-1]
    filename = re.sub(r"[^A-Za-z0-9_.-]", "_", filename)
    filename = filename.lstrip("._")
    return filename or "file"
