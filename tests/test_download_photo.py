from pathlib import Path

from downloader import ShutterflyDownloader
from .conftest import FakeResponse


def test_download_photo_duplicate_name_creates_unique(monkeypatch, downloader_factory, tmp_output_dir):
    d = downloader_factory()
    album = "AlbumA"
    content1 = b"AAAABBBB"
    content2 = b"CCCCDDDDXXXX"  # different size

    responses = [
        FakeResponse(headers={"content-disposition": "attachment; filename=IMG_1.jpg"}, content_bytes=content1),
        FakeResponse(headers={"content-disposition": "attachment; filename=IMG_1.jpg"}, content_bytes=content2),
    ]

    def fake_make_request(method, url, **kwargs):
        assert method == "get"
        return responses.pop(0)

    monkeypatch.setattr(ShutterflyDownloader, "make_request", staticmethod(fake_make_request))

    stats = {"same_name_count": 0, "different_size": 0, "different_content": 0}
    seen = set()
    assert d.download_photo("m1", album, 1, seen, stats)
    assert d.download_photo("m2", album, 2, seen, stats)

    album_dir = d.output_dir / d.sanitize_filename(album)
    files = sorted(p.name for p in album_dir.iterdir() if p.is_file())
    # Expect IMG_1.jpg and IMG_1_1.jpg
    assert files[0].startswith("IMG_1") and files[1].startswith("IMG_1") and files[0] != files[1]
    assert stats["same_name_count"] == 1
    assert stats["different_size"] == 1


