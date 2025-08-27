import base64
import json
import time
from pathlib import Path

import pytest

from downloader import ShutterflyDownloader


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def make_token(exp_delta_seconds: int = 3600, sfly_uid: str = "user123") -> str:
    header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = {"exp": int(time.time()) + exp_delta_seconds, "sfly_uid": sfly_uid}
    body = _b64url(json.dumps(payload).encode())
    sig = ""  # signature unused
    return f"{header}.{body}.{sig}"


class FakeResponse:
    def __init__(self, *, json_data=None, status_code=200, headers=None, content_bytes: bytes = b""):
        self._json_data = json_data
        self.status_code = status_code
        self.headers = headers or {}
        self._content_bytes = content_bytes

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self._content_bytes), chunk_size):
            yield self._content_bytes[i : i + chunk_size]


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "out"
    d.mkdir()
    return d


@pytest.fixture
def token() -> str:
    return make_token()


@pytest.fixture
def downloader_factory(token, tmp_output_dir):
    def _factory(**overrides):
        return ShutterflyDownloader(
            access_token=overrides.get("access_token", token),
            output_dir=overrides.get("output_dir", tmp_output_dir),
            rate_limit_delay=overrides.get("rate_limit_delay", 0.0),
            ignore_albums=overrides.get("ignore_albums", None),
            max_parallel_workers=overrides.get("max_parallel_workers", 1),
        )

    return _factory


# Scrubbed sample payloads based on real responses
@pytest.fixture
def sample_get_albums_payload():
    return {
        "result": {
            "_explicitType": "ResponseWrapper",
            "success": True,
            "errors": None,
            "message": "Success.",
            "payload": [
                [
                    {
                        "_explicitType": "StoryPermission",
                        "uid": "perm-1",
                        "story_uid": "story-111",
                        "life_uid": "000000000000",
                        "person_uid": "000000000000",
                        "first_name": "User",
                        "last_name": "Example",
                        "owner_person_uid": "000000000000",
                        "name": "User",
                        "accepted": True,
                        "view_only": False,
                        "follow": True,
                        "blocked": False,
                        "story": {
                            "_explicitType": "Story",
                            "uid": "story-111",
                            "life_uid": "000000000000",
                            "name": "Test",
                            "visible_moment_count": 14,
                        },
                        "email_notification": True,
                    },
                    {
                        "_explicitType": "StoryPermission",
                        "uid": "perm-2",
                        "story_uid": "story-222",
                        "life_uid": "000000000000",
                        "person_uid": "000000000000",
                        "first_name": "User",
                        "last_name": "Example",
                        "owner_person_uid": "000000000000",
                        "name": "User",
                        "accepted": True,
                        "view_only": False,
                        "follow": True,
                        "blocked": False,
                        "story": {
                            "_explicitType": "Story",
                            "uid": "story-222",
                            "life_uid": "000000000000",
                            "name": "test as well",
                            "visible_moment_count": 6,
                        },
                        "email_notification": True,
                    },
                ],
                [],
                [],
            ],
        },
        "id": "",
        "error": None,
    }


@pytest.fixture
def sample_get_album_payload():
    return {
        "result": {
            "_explicitType": "ResponseWrapper",
            "success": True,
            "errors": None,
            "message": "Success.",
            "payload": {
                "_explicitType": "Story",
                "uid": "story-222",
                "life_uid": "000000000000",
                "name": "test as well",
                "moments": "15f41cd721819306514645308676a6703010a010800676a6703027056538841676a67036b299a40d05a5c352d2d2d2d2d2d30302d6e335734386f443932764c66796a544e524a4f786b414e4970564d78566a484252576556376c7542523474615f54574c5156623042364879714545744e794161556e446e75346748485770667959713557777a6d4e67161afa8c01819306040460208676a670103a603b400676a6701027056538841676a6701969b4da0f1b7aaf62d2d2d2d2d2d30302d6e335734386f443932764c66796a544e524a4f786b414e4970564d78566a484252576556376c75425234734e797947676b675f65657043784978756373695639556e446e75346748485770667959713557777a6d4e6716385a4001819306488463593676a66ba0fc00bd000676a66ba027056538841676a66ba7718a8e7995ca40a2d2d2d2d2d2d30302d6e335734386f443932764c66796a544e524a4f786b414e4970564d78566a484252576556376c754252347358615a5870545352747639673658582d51564e70426c644d544c6662744a5f5f77595642515f3469546f77164eae9401819306427646407676a67030ba00bb800676a6703027056538841676a670353c83b203b24b3a92d2d2d2d2d2d30302d6e335734386f443932764c66796a544e524a4f786b414e4970564d78566a484252576556376c75425234754f466b673034766352514a75506e57585f7a78623534784a32547775373551465f6a697a4d6b42315a6441165725da71819306145153843676a670001c2021c00676a6700027056538841676a6700038b8e8426fc28ae2d2d2d2d2d2d30302d6e335734386f443932764c66796a544e524a4f786b414e4970564d78566a484252576556376c754252347453646d386d666c316c705a42614734666a794241556c644d544c6662744a5f5f77595642515f3469546f77166076a011819306364273173676a6700019d022600676a6700027056538841676a6700d3b05124e86f3b4b2d2d2d2d2d2d30302d6e335734386f443932764c66796a544e524a4f786b414e4970564d78566a484252576556376c7542523474526131754873784c562d58535f424a66795f4d31426c644d544c6662744a5f5f77595642515f3469546f77",
                "visible_moment_count": 6,
                "filenames": [
                    "Screen Shot 2020-08-22 at 6.59.08 PM.jpg",
                    "Screen Shot 2021-12-07 at 10.32.25 AM.jpg",
                    "IMG_1634.jpg",
                    "screen_alignment1.jpg",
                    "tumblr_f95229c182bd22f1acbe5e7e6fca4358_a2142567_540.jpg",
                    "kim-murray-snow-leopard-mtn-murmer.jpg",
                ],
                "shared": False,
            },
        },
        "id": "",
        "error": None,
    }


