"""Backend tests: Steam scanning, the HTTP server's protections, and the store parsing.

Run from launcher-web/:   python -m unittest discover -s tests -v
No network and no real Steam are used; the launch functions are replaced so nothing is ever started.
"""
import json
import os
import shutil
import sqlite3
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
import heroic  # noqa: E402
import lutris  # noqa: E402
import server  # noqa: E402
import settings  # noqa: E402
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


class LutrisScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = fixture.build_lutris(self.tmp.name)
        self._env = os.environ.get("DARKSHAM_LUTRIS")
        os.environ["DARKSHAM_LUTRIS"] = str(self.dir)

    def tearDown(self):
        if self._env is None:
            os.environ.pop("DARKSHAM_LUTRIS", None)
        else:
            os.environ["DARKSHAM_LUTRIS"] = self._env
        self.tmp.cleanup()

    def test_installed_games_only_most_recent_first(self):
        games = lutris.scan()
        self.assertEqual([g["id"] for g in games], ["lutris:5", "lutris:6"])
        self.assertEqual(games[0]["title"], "Lutris Game A")
        self.assertEqual((games[0]["source"], games[0]["runner"], games[0]["platform"]), ("lutris", "wine", "Windows"))

    def test_playtime_is_already_in_hours(self):
        self.assertEqual(lutris.scan()[0]["hours"], 3.5)

    def test_art_prefers_cover_then_banner(self):
        g = {x["appid"]: x for x in lutris.scan()}
        self.assertEqual(g["5"]["files"]["cover"].name, "lutris-game-a.jpg")
        self.assertEqual(g["6"]["files"]["cover"].name, "lutris-game-b.png")

    def test_database_is_opened_read_only(self):
        before = (self.dir / "pga.db").read_bytes()
        lutris.scan()
        self.assertEqual((self.dir / "pga.db").read_bytes(), before)

    def test_older_database_without_optional_columns_still_works(self):
        db = self.dir / "pga.db"
        db.unlink()
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE games (id INTEGER PRIMARY KEY, name TEXT)")
        con.execute("INSERT INTO games VALUES (1, 'Old Schema Game')")
        con.commit()
        con.close()
        games = lutris.scan()
        self.assertEqual([g["title"] for g in games], ["Old Schema Game"])
        self.assertEqual(games[0]["hours"], 0.0)

    def test_broken_or_missing_database_gives_an_empty_library(self):
        (self.dir / "pga.db").write_bytes(b"this is not a database")
        self.assertEqual(lutris.scan(), [])
        shutil.rmtree(self.dir)
        self.assertEqual(lutris.scan(), [])

    def test_launch_refuses_anything_but_digits(self):
        for bad in ("", "5 & calc", "../x", "5;rm", "lutris:5", "-1"):
            self.assertEqual(lutris.launch(bad)[0], False, bad)


class HeroicScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = fixture.build_heroic(self.tmp.name)
        self._env = os.environ.get("DARKSHAM_HEROIC")
        os.environ["DARKSHAM_HEROIC"] = str(self.dir)

    def tearDown(self):
        if self._env is None:
            os.environ.pop("DARKSHAM_HEROIC", None)
        else:
            os.environ["DARKSHAM_HEROIC"] = self._env
        self.tmp.cleanup()

    def test_installed_games_from_epic_gog_and_amazon(self):
        g = {x["id"]: x for x in heroic.scan()}
        self.assertEqual(set(g), {"heroic:legendary:EpicApp1", "heroic:gog:1207658930", "heroic:nile:amzn1.adg.abc"})
        self.assertEqual((g["heroic:legendary:EpicApp1"]["title"], g["heroic:legendary:EpicApp1"]["store"]), ("Epic Game", "Epic"))
        self.assertEqual((g["heroic:gog:1207658930"]["title"], g["heroic:gog:1207658930"]["store"]), ("GOG Game", "GOG"))
        self.assertEqual((g["heroic:nile:amzn1.adg.abc"]["title"], g["heroic:nile:amzn1.adg.abc"]["store"]), ("Amazon Game", "Amazon"))

    def test_dlc_uninstalled_and_unnamed_entries_are_left_out(self):
        ids = {x["id"] for x in heroic.scan()}
        self.assertNotIn("heroic:legendary:EpicDlc1", ids)       # DLC
        self.assertNotIn("heroic:gog:999", ids)                  # installed, but no title in the library
        self.assertNotIn("heroic:gog:555", ids)                  # in the library, not installed
        self.assertNotIn("heroic:nile:amzn1.adg.def", ids)       # no install path
        self.assertFalse([i for i in ids if " " in i], "app names with unsafe characters must be dropped")

    def test_old_gog_library_location_is_still_read(self):
        (self.dir / "store_cache" / "gog_library.json").rename(self.dir / "gog_store" / "library.json")
        self.assertIn("heroic:gog:1207658930", {x["id"] for x in heroic.scan()})

    def test_games_without_art_get_stable_distinct_colours(self):
        a, b = heroic.scan(), heroic.scan()
        self.assertEqual([x["accent"] for x in a], [x["accent"] for x in b])
        self.assertEqual(len({x["accent"] for x in a}), len(a))
        for x in a:
            self.assertEqual(x["files"], {})
            self.assertRegex(x["accent"], r"^#[0-9a-f]{6}$")

    def test_broken_files_are_skipped_not_fatal(self):
        (self.dir / "legendaryConfig" / "legendary" / "installed.json").write_text("{ not json", encoding="utf-8")
        (self.dir / "gog_store" / "installed.json").write_text("[]", encoding="utf-8")
        self.assertEqual([x["id"] for x in heroic.scan()], ["heroic:nile:amzn1.adg.abc"])
        shutil.rmtree(self.dir)
        self.assertEqual(heroic.scan(), [])

    def test_launch_validates_runner_and_name(self):
        for runner, app in (("sideload", "x"), ("steam", "x"), ("gog", ""), ("gog", "a b"), ("gog", "../x"), ("legendary", "a&b"),
                            ("legendary", "x" * 65), ("gog", "a\nb"), ("", "x")):
            self.assertEqual(heroic.launch(runner, app)[0], False, (runner, app))


class SettingsFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._env = os.environ.get("DARKSHAM_SETTINGS"), os.environ.get("DARKSHAM_CC")
        os.environ["DARKSHAM_SETTINGS"] = str(Path(self.tmp.name) / "sub" / "settings.json")
        os.environ.pop("DARKSHAM_CC", None)

    def tearDown(self):
        for var, old in zip(("DARKSHAM_SETTINGS", "DARKSHAM_CC"), self._env):
            if old is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = old
        self.tmp.cleanup()

    def test_missing_file_gives_defaults(self):
        self.assertEqual(settings.load(), {"region": "us", "sources": {"steam": True, "lutris": True, "heroic": True}})

    def test_default_region_can_come_from_the_environment(self):
        os.environ["DARKSHAM_CC"] = "DE"
        self.assertEqual(settings.load()["region"], "de")
        os.environ["DARKSHAM_CC"] = "zz"
        self.assertEqual(settings.load()["region"], "us")

    def test_update_persists_and_merges(self):
        data, problems = settings.update({"region": "tr", "sources": {"heroic": False}})
        self.assertEqual(problems, [])
        self.assertEqual(data["region"], "tr")
        data, _ = settings.update({"sources": {"steam": False}})
        again = settings.load()
        self.assertEqual((again["region"], again["sources"]), ("tr", {"steam": False, "lutris": True, "heroic": False}))

    def test_a_bad_patch_saves_nothing(self):
        settings.update({"region": "tr"})
        data, problems = settings.update({"region": "gb", "bogus": 1})
        self.assertTrue(problems)
        self.assertEqual(settings.load()["region"], "tr")

    def test_hand_edited_garbage_falls_back_to_defaults(self):
        p = settings.path()
        p.parent.mkdir(parents=True)
        p.write_text("{ not json")
        self.assertEqual(settings.load()["region"], "us")
        p.write_text(json.dumps({"region": "moon", "sources": {"steam": "yes", "lutris": False}, "extra": 1}))
        data = settings.load()
        self.assertEqual((data["region"], data["sources"]), ("us", {"steam": True, "lutris": False, "heroic": True}))


class ServerProtections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.steam_dir = fixture.build(cls.tmp.name)
        cls.lutris_dir = fixture.build_lutris(cls.tmp.name)
        cls.heroic_dir = fixture.build_heroic(cls.tmp.name)
        cls._senv, cls._cc = os.environ.get("DARKSHAM_SETTINGS"), store.CC
        os.environ["DARKSHAM_SETTINGS"] = str(Path(cls.tmp.name) / "settings.json")
        cls._env = os.environ.get("DARKSHAM_LUTRIS")
        cls._henv = os.environ.get("DARKSHAM_HEROIC")
        os.environ["DARKSHAM_LUTRIS"] = str(cls.lutris_dir)
        os.environ["DARKSHAM_HEROIC"] = str(cls.heroic_dir)
        cls._find = steam.find_steam
        steam.find_steam = lambda hint=None: cls.steam_dir
        # never start anything for real: record the calls instead
        cls.started, cls.opened, cls.lutris_started, cls.heroic_started = [], [], [], []
        cls._launch, cls._open, cls._llaunch, cls._hlaunch = steam.launch, steam.open_store, lutris.launch, heroic.launch
        heroic.launch = lambda runner, app, flatpak=False: (cls.heroic_started.append((runner, app)) or True, "started")
        steam.launch = lambda appid: (cls.started.append(appid) or True, "started")
        steam.open_store = lambda appid: (cls.opened.append(appid) or True, "opened")
        lutris.launch = lambda gid, flatpak=False: (cls.lutris_started.append(gid) or True, "started")
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.port

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        steam.find_steam, steam.launch, steam.open_store, lutris.launch, heroic.launch = cls._find, cls._launch, cls._open, cls._llaunch, cls._hlaunch
        store.CC = cls._cc
        for var, old in (("DARKSHAM_LUTRIS", cls._env), ("DARKSHAM_HEROIC", cls._henv), ("DARKSHAM_SETTINGS", cls._senv)):
            if old is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = old
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
        # Steam and Lutris merged, most recently played first (ties keep Steam first)
        self.assertEqual([g["id"] for g in games], ["steam:1001", "lutris:5", "steam:1002", "steam:1003", "lutris:6",
                                                    "heroic:nile:amzn1.adg.abc", "heroic:legendary:EpicApp1", "heroic:gog:1207658930"])  # zero-time ties keep source order, Heroic alphabetical by title
        self.assertEqual(games[0]["cover"], "/art/steam-1001/cover")
        self.assertEqual(games[1]["cover"], "/art/lutris-5/cover")
        self.assertNotIn("files", games[0])  # file system paths never leave the server
        self.assertEqual(self.req("/art/steam-1001/cover")[0], 200)
        self.assertEqual(self.req("/art/lutris-5/cover")[0], 200)
        self.assertEqual(self.req("/art/lutris-6/cover")[0], 200)   # no cover art, the banner is used
        self.assertEqual(self.req("/art/steam-1003/cover")[0], 404)
        self.assertEqual(self.req("/art/steam-999/cover")[0], 404)
        self.assertEqual(self.req("/art/1001/cover")[0], 404)        # the old id-only form is gone
        self.assertEqual(self.req("/art/heroic-legendary-EpicApp1/cover")[0], 404)   # Heroic games have no local art
        self.assertNotIn("cover", games[5])

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
        n, ln, hn = len(self.started), len(self.lutris_started), len(self.heroic_started)
        for bad in ("steam:1001 & calc", "steam:../x", "1001", "steam:", "steam:99999999999999", "", None, 5,
                    "lutris:5 & calc", "lutris:../x", "lutris:", "gog:1", "steam:1001\nlutris:5"):
            self.assertEqual(self.post("/api/launch", {"id": bad})[0], 400, bad)
        self.assertEqual(self.post("/api/launch", {"id": "steam:4242424"})[0], 404)  # not installed
        self.assertEqual(self.post("/api/launch", {"id": "lutris:7"})[0], 404)       # in the database but not installed
        self.assertEqual(self.post("/api/launch", {"id": "lutris:99"})[0], 404)
        for bad in ("heroic:sideload:x", "heroic:gog:x y", "heroic:gog:../x", "heroic:legendary:", "heroic:legendary:a&b", "heroic:legendary:EpicApp1\n"):
            self.assertEqual(self.post("/api/launch", {"id": bad})[0], 400, bad)
        self.assertEqual(self.post("/api/launch", {"id": "heroic:gog:777"})[0], 404)            # not installed
        self.assertEqual(self.post("/api/launch", {"id": "heroic:legendary:EpicDlc1"})[0], 404)  # DLC is not a game
        self.assertEqual((len(self.started), len(self.lutris_started), len(self.heroic_started)), (n, ln, hn), "nothing may start for a bad id")

    def test_launch_of_an_installed_game_starts_exactly_that_game(self):
        n = len(self.started)
        code, body, _ = self.post("/api/launch", {"id": "steam:1002"})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["ok"], True)
        self.assertEqual(self.started[n:], ["1002"])

    def test_lutris_launch_goes_to_lutris_not_steam(self):
        n, m = len(self.started), len(self.lutris_started)
        code, body, _ = self.post("/api/launch", {"id": "lutris:5"})
        self.assertEqual(code, 200)
        self.assertEqual(self.lutris_started[m:], ["5"])
        self.assertEqual(self.started[n:], [])
        self.assertEqual(self.post("/api/launch", {"id": "lutris:5"}, token=False)[0], 403)
        self.assertEqual(self.lutris_started[m:], ["5"], "a refused request must not launch")

    def test_heroic_launch_goes_to_heroic_with_runner_and_app(self):
        n = len(self.heroic_started)
        self.assertEqual(self.post("/api/launch", {"id": "heroic:gog:1207658930"})[0], 200)
        self.assertEqual(self.post("/api/launch", {"id": "heroic:legendary:EpicApp1"})[0], 200)
        self.assertEqual(self.post("/api/launch", {"id": "heroic:nile:amzn1.adg.abc"})[0], 200)
        self.assertEqual(self.heroic_started[n:], [("gog", "1207658930"), ("legendary", "EpicApp1"), ("nile", "amzn1.adg.abc")])
        self.assertEqual(self.post("/api/launch", {"id": "heroic:gog:1207658930"}, token=False)[0], 403)
        self.assertEqual(len(self.heroic_started), n + 3)

    # ---- settings
    def settings(self):
        return json.loads(self.req("/api/settings")[1])

    def test_settings_defaults_and_what_was_found(self):
        s = self.settings()
        self.assertEqual(s["region"], "us")
        self.assertEqual({k: v["enabled"] for k, v in s["sources"].items()}, {"steam": True, "lutris": True, "heroic": True})
        self.assertEqual({k: v["found"] for k, v in s["sources"].items()}, {"steam": 3, "lutris": 2, "heroic": 3})
        self.assertIn("sa", s["regions"])

    def test_settings_changes_need_the_token_and_valid_values(self):
        before = self.settings()
        self.assertEqual(self.post("/api/settings", {"region": "sa"}, token=False)[0], 403)
        self.assertEqual(self.post("/api/settings", {"region": "sa"}, headers={"Origin": "https://evil.example"})[0], 403)
        for bad in ({"region": "xx"}, {"region": "us; rm -rf"}, {"region": 5}, {"region": None}, {"colour": "red"},
                    {"sources": {"epic": False}}, {"sources": {"steam": "no"}}, {"sources": []}, [], "region"):
            self.assertEqual(self.post("/api/settings", bad)[0], 400, bad)
        self.assertEqual(self.settings(), before, "a refused change must not change anything")

    def test_valid_settings_are_saved_and_applied(self):
        code, body, _ = self.post("/api/settings", {"region": "sa"})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["region"], "sa")
        self.assertEqual(self.settings()["region"], "sa")
        self.assertEqual(store.CC, "sa")
        self.assertEqual(json.loads(Path(os.environ["DARKSHAM_SETTINGS"]).read_text())["region"], "sa")
        self.post("/api/settings", {"region": "us"})
        self.assertEqual(store.CC, "us")

    def test_disabling_a_source_hides_its_games_and_refuses_its_launch(self):
        n = len(self.lutris_started)
        self.assertEqual(self.post("/api/settings", {"sources": {"lutris": False}})[0], 200)
        try:
            ids = [g["id"] for g in json.loads(self.req("/api/library")[1])["games"]]
            self.assertFalse([i for i in ids if i.startswith("lutris:")])
            self.assertIn("steam:1001", ids)
            self.assertEqual(self.post("/api/launch", {"id": "lutris:5"})[0], 404)
            self.assertEqual(len(self.lutris_started), n)
            self.assertEqual(self.settings()["sources"]["lutris"]["found"], 2, "the count shows what exists even when hidden")
        finally:
            self.post("/api/settings", {"sources": {"lutris": True}})
        self.assertIn("lutris:5", [g["id"] for g in json.loads(self.req("/api/library")[1])["games"]])

    def test_clear_cache_only_removes_cache_files(self):
        root = Path(self.tmp.name) / "cache"
        (root / "json").mkdir(parents=True)
        (root / "img").mkdir()
        for name in ("json/a.json", "json/b.json", "img/c", "img/c.type"):
            (root / name).write_text("x")
        (root / "json" / "sub").mkdir()
        (root / "json" / "sub" / "keep-inside").write_text("x")
        (root / "keep.txt").write_text("x")
        old = store.ROOT
        store.ROOT = root
        try:
            self.assertEqual(self.post("/api/settings/clear-cache", {}, token=False)[0], 403)
            self.assertTrue((root / "json" / "a.json").exists())
            code, body, _ = self.post("/api/settings/clear-cache", {})
        finally:
            store.ROOT = old
        self.assertEqual((code, json.loads(body)["removed"]), (200, 4))
        self.assertTrue((root / "keep.txt").exists() and (root / "json" / "sub" / "keep-inside").exists())
        self.assertFalse((root / "json" / "a.json").exists())

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
