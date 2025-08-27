from downloader import ShutterflyDownloader


def test_compare_local_vs_server(monkeypatch, downloader_factory, tmp_output_dir, capsys):
    d = downloader_factory()

    server_albums = [
        {"id": "1", "name": "A", "photo_count": 2},
        {"id": "2", "name": "B", "photo_count": 3},
    ]

    # Create local: A has 1 file (missing 1), C is extra
    a_dir = d.output_dir / "A"
    a_dir.mkdir()
    (a_dir / "f1.jpg").write_bytes(b"x")
    c_dir = d.output_dir / "C"
    c_dir.mkdir()
    (c_dir / "g1.jpg").write_bytes(b"x")

    monkeypatch.setattr(ShutterflyDownloader, "get_albums", lambda self: server_albums)

    d.compare_local_vs_server()
    out = capsys.readouterr().out
    assert "Missing 1" in out
    assert "Not downloaded" in out  # for B
    assert "Local only" in out  # for C


