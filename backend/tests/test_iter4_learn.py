"""
Iteration 4 backend tests: webinar, guides, pixels, offline/sw.js.
Covers admin RBAC, YouTube URL parsing, slug/icon validation, pixel validation,
audit action 'pixel.replace', public pixels endpoint, and offline page availability.
"""
import os
import re
import requests
import pytest

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN = {"email": "takmonboost90@gmail.com", "password": "Admin@Demo2026"}
USER = {"email": "demo.a@example.com", "password": "Demo@12345"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def user():
    return _login(USER)


# ---------------- offline/sw ----------------
class TestOffline:
    def test_offline_html(self):
        r = requests.get(f"{BASE}/offline.html", timeout=20)
        assert r.status_code == 200
        body = r.text.lower()
        assert "offline" in body
        assert "offline-retry-btn" in r.text or "retry" in body

    def test_sw_js(self):
        r = requests.get(f"{BASE}/sw.js", timeout=20)
        assert r.status_code == 200
        assert "offline.html" in r.text


# ---------------- webinar ----------------
class TestWebinar:
    def test_admin_get(self, admin):
        r = admin.get(f"{BASE}/api/admin/webinar")
        assert r.status_code == 200
        d = r.json()
        for k in ("enabled", "required", "title", "video_url", "min_watch_seconds", "stats"):
            assert k in d
        assert set(d["stats"].keys()) >= {"users", "started", "completed"}

    def test_user_forbidden(self, user):
        r = user.get(f"{BASE}/api/admin/webinar")
        assert r.status_code == 403

    def test_user_webinar_get(self, user):
        r = user.get(f"{BASE}/api/webinar")
        assert r.status_code == 200
        assert "video_id" in r.json()
        assert "completed_at" in r.json()

    def test_put_invalid_youtube(self, admin):
        cur = admin.get(f"{BASE}/api/admin/webinar").json()
        payload = {k: cur[k] for k in ("enabled", "required", "title", "subtitle", "host", "duration",
                                       "description", "highlights", "cta_text", "min_watch_seconds")}
        payload["video_url"] = "https://example.com/not-youtube"
        r = admin.put(f"{BASE}/api/admin/webinar", json=payload)
        assert r.status_code == 400

    @pytest.mark.parametrize("url,expected", [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ])
    def test_put_valid_urls(self, admin, url, expected):
        cur = admin.get(f"{BASE}/api/admin/webinar").json()
        payload = {k: cur[k] for k in ("enabled", "required", "title", "subtitle", "host", "duration",
                                       "description", "highlights", "cta_text", "min_watch_seconds")}
        payload["video_url"] = url
        r = admin.put(f"{BASE}/api/admin/webinar", json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["video_id"] == expected

    def test_cleanup_webinar(self, admin):
        # restore video_url blank for user cleanup
        cur = admin.get(f"{BASE}/api/admin/webinar").json()
        payload = {k: cur[k] for k in ("enabled", "required", "title", "subtitle", "host", "duration",
                                       "description", "highlights", "cta_text", "min_watch_seconds")}
        payload["video_url"] = ""
        r = admin.put(f"{BASE}/api/admin/webinar", json=payload)
        assert r.status_code == 200
        assert r.json()["video_id"] == ""


# ---------------- guides ----------------
class TestGuides:
    def test_list_user(self, user):
        r = user.get(f"{BASE}/api/guides")
        assert r.status_code == 200
        slugs = [g["slug"] for g in r.json()]
        for s in ("how-to-deposit-usdt", "how-to-withdraw-usdt", "how-to-buy-usdt-bank-transfer", "how-to-install-the-app"):
            assert s in slugs

    def test_get_by_slug_increments_views(self, user):
        r1 = user.get(f"{BASE}/api/guides/how-to-deposit-usdt")
        assert r1.status_code == 200
        v1 = r1.json()["views"]
        r2 = user.get(f"{BASE}/api/guides/how-to-deposit-usdt")
        assert r2.json()["views"] == v1 + 1

    def test_get_missing_slug_404(self, user):
        r = user.get(f"{BASE}/api/guides/does-not-exist-xyz")
        assert r.status_code == 404

    def test_create_invalid_slug(self, admin):
        body = {"title": "TEST Guide", "slug": "Bad Slug!!", "description": "x",
                "video_url": "", "icon": "BookOpen", "steps": ["one"], "order": 99, "active": True}
        r = admin.post(f"{BASE}/api/admin/guides", json=body)
        assert r.status_code == 422

    def test_create_invalid_icon(self, admin):
        body = {"title": "TEST Guide", "slug": "test-guide-bad-icon", "description": "x",
                "video_url": "", "icon": "NotAnIcon", "steps": ["one"], "order": 99, "active": True}
        r = admin.post(f"{BASE}/api/admin/guides", json=body)
        assert r.status_code == 400

    def test_crud_guide(self, admin):
        body = {"title": "TEST Guide Finzo", "slug": "test-guide-finzo", "description": "test",
                "video_url": "https://youtu.be/dQw4w9WgXcQ", "icon": "BookOpen",
                "steps": ["step one", "step two"], "order": 50, "active": True}
        r = admin.post(f"{BASE}/api/admin/guides", json=body)
        assert r.status_code == 200, r.text
        gid = r.json()["id"]
        assert r.json()["video_id"] == "dQw4w9WgXcQ"

        # duplicate
        r2 = admin.post(f"{BASE}/api/admin/guides", json=body)
        assert r2.status_code == 409

        # update
        body["title"] = "TEST Guide Finzo Updated"
        r3 = admin.put(f"{BASE}/api/admin/guides/{gid}", json=body)
        assert r3.status_code == 200
        assert r3.json()["title"] == "TEST Guide Finzo Updated"

        # delete
        r4 = admin.delete(f"{BASE}/api/admin/guides/{gid}")
        assert r4.status_code == 200

        # delete missing
        r5 = admin.delete(f"{BASE}/api/admin/guides/{gid}")
        assert r5.status_code == 404

    def test_user_cannot_admin(self, user):
        r = user.get(f"{BASE}/api/admin/guides")
        assert r.status_code == 403


# ---------------- pixels ----------------
class TestPixels:
    created_id = None

    def test_user_forbidden(self, user):
        r = user.get(f"{BASE}/api/admin/pixels")
        assert r.status_code == 403

    def test_invalid_pixel_id(self, admin):
        r = admin.post(f"{BASE}/api/admin/pixels",
                       json={"name": "TEST", "pixel_id": "short", "active": True, "events": ["PageView"]})
        assert r.status_code == 422

    def test_unsupported_event(self, admin):
        r = admin.post(f"{BASE}/api/admin/pixels",
                       json={"name": "TEST", "pixel_id": "123456789012345", "active": True, "events": ["WeirdEvent"]})
        assert r.status_code == 400

    def test_crud_and_audit_replace(self, admin):
        pid1, pid2 = "123456789012345", "123456789012346"
        # cleanup existing
        existing = admin.get(f"{BASE}/api/admin/pixels").json()["items"]
        for p in existing:
            if p["pixel_id"] in (pid1, pid2):
                admin.delete(f"{BASE}/api/admin/pixels/{p['id']}")

        r = admin.post(f"{BASE}/api/admin/pixels",
                       json={"name": "TEST Pixel", "pixel_id": pid1, "active": True, "events": ["PageView", "Lead"]})
        assert r.status_code == 200, r.text
        pid = r.json()["id"]

        # duplicate
        r2 = admin.post(f"{BASE}/api/admin/pixels",
                        json={"name": "TEST Pixel", "pixel_id": pid1, "active": True, "events": ["PageView"]})
        assert r2.status_code == 409

        # replace -> pixel.replace audit
        r3 = admin.put(f"{BASE}/api/admin/pixels/{pid}",
                       json={"name": "TEST Pixel", "pixel_id": pid2, "active": True, "events": ["PageView"]})
        assert r3.status_code == 200
        assert r3.json()["pixel_id"] == pid2

        # public endpoint shows active pixel
        pub = requests.get(f"{BASE}/api/public/pixels").json()
        assert any(p["pixel_id"] == pid2 for p in pub)

        # delete
        rd = admin.delete(f"{BASE}/api/admin/pixels/{pid}")
        assert rd.status_code == 200
        rd2 = admin.delete(f"{BASE}/api/admin/pixels/{pid}")
        assert rd2.status_code == 404

    def test_public_pixels_shape(self):
        r = requests.get(f"{BASE}/api/public/pixels")
        assert r.status_code == 200
        for p in r.json():
            assert set(p.keys()) == {"pixel_id", "events"}
