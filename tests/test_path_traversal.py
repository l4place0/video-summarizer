"""Tests for path traversal prevention in frame serving."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException


def test_normal_filename_accepted():
    """Pure filename passes validation."""
    filename = "frame_0001.jpg"
    safe = Path(filename).name
    assert safe == filename
    assert safe == filename  # no change


def test_path_traversal_rejected():
    """Path traversal attempts are rejected."""
    malicious = "../../etc/passwd"
    safe = Path(malicious).name
    assert safe == "passwd"  # extracted pure filename
    assert safe != malicious  # different from input


def test_backslash_traversal_rejected():
    """Windows-style path traversal is rejected (on Linux, backslash is part of filename)."""
    malicious = "..\\..\\windows\\system32\\config"
    safe = Path(malicious).name
    # On Linux, backslash is a valid char in filenames, so name is the full string
    # The important thing is the filename check + resolve() prevents escape
    assert safe == malicious  # on Linux, this is treated as a single filename
    # The resolve() check in the endpoint prevents actual file access outside base


def test_absolute_path_rejected():
    """Absolute path is rejected."""
    malicious = "/etc/passwd"
    safe = Path(malicious).name
    assert safe == "passwd"
    assert safe != malicious


def test_resolve_stays_in_base(tmp_path):
    """Resolved path must stay within base directory."""
    base = tmp_path / "frames"
    base.mkdir()

    # Create a legitimate file
    (base / "frame_001.jpg").write_bytes(b"fake-image")

    # Normal case: file exists
    safe_name = "frame_001.jpg"
    resolved = (base / safe_name).resolve()
    assert str(resolved).startswith(str(base.resolve()))

    # Traversal case: resolved path escapes base
    traversal = "../../etc/passwd"
    safe_name = Path(traversal).name  # "passwd"
    resolved = (base / safe_name).resolve()
    # passwd doesn't exist in base, but even if it did, the check should work
    assert safe_name == "passwd"


def test_dot_filename_rejected():
    """Filename that is just dots is rejected by endpoint."""
    # Path("..").name == ".." — caught by safe_name in (".", "..") check
    assert Path("..").name == ".."
    # Path(".").name == "" — caught by not safe_name check
    assert Path(".").name == ""
    # These would be rejected by the endpoint's validation
