from downloader import ShutterflyDownloader
from .conftest import FakeResponse


def test_get_albums_cookie_requires_life_uid(monkeypatch, downloader_factory):
    # Using session cookie should require LIFE_UID; simulate with fake cookie
    cookie = "_thislife_session=abc123"
    d = downloader_factory(access_token=cookie)

    # Without LIFE_UID, get_albums should prompt; we simulate by raising on input
    # Instead, set LIFE_UID to avoid prompt and verify payload params
    monkeypatch.setenv("LIFE_UID", "user-cookie-uid")

    def fake_make_request(method, url, **kwargs):
        assert method == "post"
        body = kwargs["json"]
        assert body["method"] == "album.getAlbums"
        params = body["params"]
        # For cookie path, first param must be LIFE_UID
        assert params[0] == "user-cookie-uid"
        return FakeResponse(json_data={"result": {"success": True, "payload": [[]]}})

    monkeypatch.setattr(ShutterflyDownloader, "make_request", staticmethod(fake_make_request))

    albums = d.get_albums()
    assert albums == []


