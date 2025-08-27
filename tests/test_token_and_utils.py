import base64
import json
import time

import pytest

from downloader import ShutterflyDownloader
from .conftest import make_token


def decode_payload(token: str):
    parts = token.split(".")
    payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64))


def test_update_access_token_sets_expiry(downloader_factory):
    d = downloader_factory(access_token=make_token(1))
    # expire soon, then update to longer
    new_tok = make_token(3600)
    d.update_access_token(new_tok)
    assert abs(d.claims["exp"] - decode_payload(new_tok)["exp"]) < 5


def test_build_download_url_contains_params(downloader_factory):
    d = downloader_factory()
    url = d.build_download_url("12345")
    assert "accessToken=" in url
    assert "momentId=12345" in url
    assert "source=library" in url


def test_sanitize_filename():
    s = ShutterflyDownloader.sanitize_filename("My: Album?/Name* ")
    assert s == "My AlbumName"


def test_extract_moment_ids_exact_slice(downloader_factory):
    d = downloader_factory()
    def make_record(moment_16: str) -> str:
        # 277 chars; place 16-char id at indices 9..25
        prefix = "x" * 9
        suffix = "y" * (277 - 9 - 16)
        return prefix + moment_16 + suffix

    rec1 = make_record("0000000000012345")
    rec2 = make_record("0000000000678901")
    moments = rec1 + rec2
    ids = d.extract_moment_ids(moments)
    assert ids == ["12345", "678901"]


