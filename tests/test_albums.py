from downloader import ShutterflyDownloader
from .conftest import FakeResponse, make_token


def test_get_albums_uses_sfly_uid(monkeypatch, downloader_factory):
    d = downloader_factory(access_token=make_token())
    # Ensure no prompt by setting LIFE_UID to match claims
    monkeypatch.setenv("LIFE_UID", d.claims["sfly_uid"]) 

    payload = {
        "result": {
            "success": True,
            "payload": [[
                {"story": {"uid": "a1", "name": "One", "visible_moment_count": 2}},
                {"story": {"uid": "a2", "name": "Two", "visible_moment_count": 3}},
            ]]
        }
    }

    def fake_make_request(method, url, **kwargs):
        assert method == "post"
        body = kwargs["json"]
        assert body["method"] == "album.getAlbums"
        params = body["params"]
        # token passed as first param, sfly_uid or LIFE_UID second
        assert params[0] == d.access_token
        assert params[1] == d.claims["sfly_uid"]
        return FakeResponse(json_data=payload)

    monkeypatch.setattr(ShutterflyDownloader, "make_request", staticmethod(fake_make_request))

    albums = d.get_albums()
    assert albums == [
        {"id": "a1", "name": "One", "photo_count": 2},
        {"id": "a2", "name": "Two", "photo_count": 3},
    ]


def test_download_album_schedules_all(monkeypatch, downloader_factory, tmp_output_dir):
    d = downloader_factory(max_parallel_workers=2)

    # 2 records -> 2 moments
    def make_moments(ids):
        def rec(moment_16):
            pre = "x" * 9
            suf = "y" * (277 - 9 - 16)
            return pre + moment_16 + suf
        return "".join(rec(i) for i in ids)

    album_payload = {
        "result": {
            "success": True,
            "payload": {
                "moments": make_moments(["0000000000000001", "0000000000000002"]) 
            },
        }
    }

    def fake_make_request(method, url, **kwargs):
        assert method == "post"
        return FakeResponse(json_data=album_payload)

    calls = []

    def fake_download_photo(moment_id, album_name, index, downloaded_files=None, duplicate_stats=None):
        calls.append((moment_id, album_name, index))
        return True

    monkeypatch.setattr(ShutterflyDownloader, "make_request", staticmethod(fake_make_request))
    monkeypatch.setattr(ShutterflyDownloader, "download_photo", staticmethod(fake_download_photo))

    ok, fail = d.download_album("album1", "My Album")
    assert ok == 2 and fail == 0
    # Order is not guaranteed due to threading, just check set
    ids = {c[0] for c in calls}
    assert ids == {"1", "2"}


