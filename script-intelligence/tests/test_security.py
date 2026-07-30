"""
VERSE Test Suite - Security Defenses and Validation Tests.
"""

import pytest
from app.utils.file_utils import sanitize_filename, validate_upload_file
from app.core.errors import SecurityError, ValidationError
from fastapi import UploadFile
import io


def test_sanitize_filename_path_traversal():
    malicious = "../../etc/passwd"
    clean = sanitize_filename(malicious)
    assert ".." not in clean
    assert clean == "passwd"


def test_sanitize_filename_windows_path():
    malicious = "C:\\Windows\\System32\\cmd.exe"
    clean = sanitize_filename(malicious)
    assert "\\" not in clean
    assert "cmd.exe" in clean


def test_validate_upload_file_invalid_extension():
    file = UploadFile(filename="script.exe", file=io.BytesIO(b"binary"))
    with pytest.raises(ValidationError):
        validate_upload_file(file)


def test_validate_upload_file_valid():
    file = UploadFile(filename="screenplay.pdf", file=io.BytesIO(b"PDF header content"))
    clean_name = validate_upload_file(file)
    assert clean_name == "screenplay.pdf"
