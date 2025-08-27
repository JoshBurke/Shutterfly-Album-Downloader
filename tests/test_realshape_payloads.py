from downloader import ShutterflyDownloader
from .conftest import FakeResponse


def test_get_albums_with_realshape(monkeypatch, downloader_factory, sample_get_albums_payload):
    d = downloader_factory()

    def fake_make_request(method, url, **kwargs):
        assert method == "post"
        body = kwargs["json"]
        assert body["method"] == "album.getAlbums"
        return FakeResponse(json_data=sample_get_albums_payload)

    monkeypatch.setattr(ShutterflyDownloader, "make_request", staticmethod(fake_make_request))
    albums = d.get_albums()
    # Validate mapping to our compact album list format
    assert albums == [
        {"id": "story-111", "name": "Test", "photo_count": 14},
        {"id": "story-222", "name": "test as well", "photo_count": 6},
    ]


def test_get_album_with_realshape(monkeypatch, downloader_factory, sample_get_album_payload):
    d = downloader_factory()

    def fake_make_request(method, url, **kwargs):
        assert method == "post"
        body = kwargs["json"]
        assert body["method"] == "album.getAlbum"
        return FakeResponse(json_data=sample_get_album_payload)

    monkeypatch.setattr(ShutterflyDownloader, "make_request", staticmethod(fake_make_request))
    data = d.get_album_contents("story-222")
    assert data["result"]["success"] is True
    moments = data["result"]["payload"]["moments"]

    # ensure our slicing works on this moments blob
    ids = d.extract_moment_ids(moments)
    assert isinstance(ids, list) and len(ids) == 6


