"""Backend tests: Steam scanning, the HTTP server's protections, and the store parsing.

Run from launcher-web/:   python -m unittest discover -s tests -v
No network and no real Steam are used; the launch functions are replaced so nothing is ever started.
"""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "backend"))

import fixture  # noqa: E402
import server  # noqa: E402
import steam  # noqa: E402
import store  # noqa: E402


class SteamScan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.steam_dir = fixture.build(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_finds_the_steam_folder_from_a_hint(self):
        self.assertEqual(steam.find_steam(str(self.steam_dir)), self.steam_dir)

    def test_reads_games_from_all_libraries_and_skips_tools(self):
        games = steam.scan(self.steam_dir)
        self.assertEqual([g["appid"] for g in games], ["1001", "1002", "1003"])  # most recently played first
        self.assertNotIn("228980", [g["appid"] for g in games])
        self.assertEqual(games[0]["title"], "Test Game One")

    def test_play_time_and_last_played(self):
        g = {x["appid"]: x for x in steam.scan(self.steam_dir)}
        self.assertEqual(g["1001"]["hours"], 10.0)
        self.assertEqual(g["1002"]["hours"], 1.5)
        self.assertEqual(g["1001"]["last_played"], 1760000000)
        self.assertEqual(g["1003"]["hours"], 0.0)

    def test_art_is_found_even_in_hash_named_subfolders(self):
        g = {x["appid"]: x for x in steam.scan(self.steam_dir)}
        self.assertEqual(set(g["1001"]["files"]), {"cover", "hero", "logo", "blur"})
        self.assertEqual(set(g["1002"]["files"]), {"hero"})
        self.assertEqual(g["1003"]["files"], {})

    def test_colours_are_hex_and_differ_per_game(self):
        g = {x["appid"]: x for x in steam.scan(self.steam_dir)}
        for x in g.values():
            self.assertRegex(x["accent"], r"^#[0-9a-f]{6}$")
            self.assertRegex(x["dark"], r"^#[0-9a-f]{6}$")
        if steam.Image:  # without Pillow every game gets the default accent
            self.assertNotEqual(g["1001"]["accent"], g["1002"]["accent"])

    def test_missing_steam_gives_an_empty_library(self):
        self.assertEqual(steam.scan(Path(self.tmp.name) / "nope"), [])

    def test_launch_refuses_anything_but_digits(self):
        for bad in ("", "570 & calc", "../x", "570;rm", "steam:570", "-1"):
            self.assertEqual(steam.launch(bad)[0], False, bad)
            self.assertEqual(steam.open_store(bad)[0], False, bad)


class ServerProtections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.steam_dir = fixture.build(cls.tmp.name)
        cls._find = steam.find_steam
        steam.find_steam = lambda hint=None: cls.steam_dir
        # never start anything for real: record the calls instead
        cls.started, cls.opened = [], []
        cls._launch, cls._open = steam.launch, steam.open_store
        steam.launch = lambda appid: (cls.started.append(appid) or True, "started")
        steam.open_store = lambda appid: (cls.opened.append(appid) or True, "opened")
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.port

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        steam.find_steam, steam.launch, steam.open_store = cls._find, cls._launch, cls._open
        cls.tmp.cleanup()

    def req(self, path, method="GET", body=None, headers=None):
        r = urllib.request.Request(self.base + path, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                return resp.status, resp.read(), resp.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers

    def post(self, path, obj, token=True, headers=None):
        h = {"Content-Type": "application/json"}
        if token:
            h["X-Darksham-Token"] = server.TOKEN
        h.update(headers or {})
        return self.req(path, "POST", json.dumps(obj).encode(), h)

    def test_ui_and_token_are_served(self):
        code, body, _ = self.req("/")
        self.assertEqual(code, 200)
        self.assertIn(server.TOKEN, body.decode())

    def test_library_api_and_art(self):
        code, body, _ = self.req("/api/library")
        games = json.loads(body)["games"]
        self.assertEqual([g["appid"] for g in games], ["1001", "1002", "1003"])
        self.assertEqual(games[0]["cover"], "/art/1001/cover")
        self.assertNotIn("files", games[0])  # file system paths never leave the server
        self.assertEqual(self.req("/art/1001/cover")[0], 200)
        self.assertEqual(self.req("/art/1003/cover")[0], 404)
        self.assertEqual(self.req("/art/999/cover")[0], 404)

    def test_static_files_and_traversal(self):
        self.assertEqual(self.req("/css/style.css")[0], 200)
        for p in ("/backend/server.py", "/tests/fixture.py", "/README.md", "/css/../backend/server.py",
                  "/fonts/..%2f..%2fCLAUDE.md", "/%2e%2e/%2e%2e/etc/passwd"):
            self.assertIn(self.req(p)[0], (403, 404), p)

    def test_other_host_headers_are_refused(self):
        self.assertEqual(self.req("/api/library", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.post("/api/launch", {"id": "steam:1001"}, headers={"Host": "evil.example"})[0], 403)

    def test_launch_needs_the_token_and_a_matching_origin(self):
        n = len(self.started)
        self.assertEqual(self.post("/api/launch", {"id": "steam:1001"}, token=False)[0], 403)
        self.assertEqual(self.post("/api/launch", {"id": "steam:1001"}, headers={"X-Darksham-Token": "wrong"})[0], 403)
        self.assertEqual(self.post("/api/launch", {"id": "steam:1001"}, headers={"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(len(self.started), n, "nothing may start without a valid request")

    def test_launch_validates_the_id(self):
        n = len(self.started)
        for bad in ("steam:1001 & calc", "steam:../x", "1001", "steam:", "steam:99999999999999", "", None, 5):
            self.assertEqual(self.post("/api/launch", {"id": bad})[0], 400, bad)
        self.assertEqual(self.post("/api/launch", {"id": "steam:4242424"})[0], 404)  # not installed
        self.assertEqual(len(self.started), n)

    def test_launch_of_an_installed_game_starts_exactly_that_game(self):
        n = len(self.started)
        code, body, _ = self.post("/api/launch", {"id": "steam:1002"})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["ok"], True)
        self.assertEqual(self.started[n:], ["1002"])

    def test_store_open_is_protected_like_launch(self):
        n = len(self.opened)
        self.assertEqual(self.post("/api/store/open", {"appid": "570"}, token=False)[0], 403)
        self.assertEqual(self.post("/api/store/open", {"appid": "570 & calc"})[0], 400)
        self.assertEqual(self.post("/api/store/open", {"appid": "../../x"})[0], 400)
        self.assertEqual(len(self.opened), n)
        self.assertEqual(self.post("/api/store/open", {"appid": "570"})[0], 200)
        self.assertEqual(self.opened[n:], ["570"])

    def test_store_routes_validate_their_input(self):
        self.assertEqual(self.req("/api/store/app/abc")[0], 404)
        self.assertEqual(self.req("/api/store/app/99999999999999999")[0], 404)
        self.assertEqual(self.req("/store-art/abc/cover")[0], 404)
        self.assertEqual(self.req("/store-img?u=https%3A%2F%2Fevil.example%2Fx.jpg")[0], 404)
        self.assertEqual(self.req("/store-img?u=http%3A%2F%2F127.0.0.1%3A{}%2Fapi%2Flibrary".format(self.port))[0], 404)


class StoreParsing(unittest.TestCase):
    FEATURED = {
        "top_sellers": {"items": [
            {"id": 11, "type": 0, "name": "Good Game", "discount_percent": 20, "original_price": 1000, "final_price": 800, "currency": "USD",
             "header_image": "https://shared.akamai.steamstatic.com/x/header.jpg", "large_capsule_image": "https://shared.akamai.steamstatic.com/x/cap.jpg"},
            {"id": 11, "type": 0, "name": "Good Game"},                       # duplicate
            {"id": 12, "type": 0, "name": "Steam Deck"},                      # hardware
            {"id": 13, "type": 0, "name": "Great Game &amp; Friends"},        # entity in the name
            {"id": 14, "type": 4, "name": "A Soundtrack"},                    # not a game
        ]},
        "specials": {"items": [{"id": 15, "type": 0, "name": "Cheap Pack DLC", "discount_percent": 50}]},
        "new_releases": {"items": []},
        "coming_soon": {"items": [{"id": 16, "type": 0, "name": "Later Game"}]},
    }

    def setUp(self):
        self._cj = store._cached_json
        store._cached_json = lambda name, url, ttl: ({"featured_win": []} if name.startswith("featured") else self.FEATURED, False)

    def tearDown(self):
        store._cached_json = self._cj

    def test_shelves_are_filtered_and_normalised(self):
        shelves = {s["id"]: s["items"] for s in store.home("en")["shelves"]}
        self.assertEqual([i["appid"] for i in shelves["top_sellers"]], [11, 13])
        self.assertEqual(shelves["top_sellers"][1]["name"], "Great Game & Friends")
        self.assertNotIn("specials", shelves)           # its only item was DLC
        self.assertEqual([i["appid"] for i in shelves["coming_soon"]], [16])
        first = shelves["top_sellers"][0]
        self.assertEqual((first["discount"], first["original"], first["final"], first["currency"]), (20, 1000, 800, "USD"))
        self.assertTrue(first["header"].startswith("https://"))

    def test_app_details_are_cleaned(self):
        raw = {"77": {"success": True, "data": {
            "name": "Test &amp; Co", "short_description": "A <b>fun</b> game &amp; more.", "type": "game",
            "genres": [{"description": "Action"}], "developers": ["Dev"], "publishers": ["Pub"],
            "release_date": {"date": "1 Jan, 2026", "coming_soon": False}, "is_free": False,
            "price_overview": {"final": 500, "initial": 1000, "discount_percent": 50, "currency": "USD", "final_formatted": "$5.00"},
            "supported_languages": "English<strong>*</strong>, Arabic, French", "platforms": {"windows": True, "linux": True},
            "screenshots": [{"path_full": "https://shared.akamai.steamstatic.com/a.jpg", "path_thumbnail": "https://shared.akamai.steamstatic.com/a_t.jpg"}]}}}
        store._cached_json = lambda name, url, ttl: (raw, False)
        d = store.app(77, "en")
        self.assertEqual(d["name"], "Test & Co")
        self.assertEqual(d["description"], "A fun game & more.")
        self.assertTrue(d["arabic"])
        self.assertEqual(d["price"]["discount"], 50)
        self.assertEqual(d["thumbs"], ["https://shared.akamai.steamstatic.com/a_t.jpg"])

    def test_unknown_app_gives_none(self):
        store._cached_json = lambda name, url, ttl: ({"5": {"success": False}}, False)
        self.assertIsNone(store.app(5, "en"))

    def test_image_proxy_only_allows_steam_cdn_over_https(self):
        for url in ("https://evil.example/x.jpg", "http://cdn.akamai.steamstatic.com/x.jpg", "file:///etc/passwd",
                    "https://cdn.akamai.steamstatic.com.evil.example/x.jpg", "ftp://cdn.akamai.steamstatic.com/x"):
            self.assertIsNone(store.image(url), url)


if __name__ == "__main__":
    unittest.main()
