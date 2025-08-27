from pathlib import Path

from downloader import ShutterflyDownloader


def test_dedupe_album_removes_exact_duplicates_keeps_different(monkeypatch, downloader_factory, tmp_output_dir):
    d = downloader_factory()
    album_dir = d.output_dir / "AlbumDupes"
    album_dir.mkdir()

    # Exact duplicate pair (identical bytes)
    (album_dir / "IMG_1.jpg").write_bytes(b"JPEGDATA-IDENTICAL")
    (album_dir / "IMG_1_1.jpg").write_bytes(b"JPEGDATA-IDENTICAL")

    # Different content but similar name pattern, same size
    content_a = b"ABCDEFGH"
    content_b = b"IJKLMNOP"  # same length as content_a
    (album_dir / "IMG_2.jpg").write_bytes(content_a)
    (album_dir / "IMG_2_1.jpg").write_bytes(content_b)

    removed = d.dedupe_album(album_dir, thorough=True)
    # Should remove exactly one (the duplicate of IMG_1)
    assert removed == 1

    remaining = sorted(p.name for p in album_dir.iterdir() if p.is_file())
    # For IMG_1 pair, the shorter name should remain
    assert "IMG_1.jpg" in remaining
    assert "IMG_1_1.jpg" not in remaining
    # For IMG_2 pair, both should remain because contents differ
    assert "IMG_2.jpg" in remaining and "IMG_2_1.jpg" in remaining


