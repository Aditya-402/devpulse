import http.client
import json
import os
import tempfile
import threading
import unittest

import server


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        server.DATA_PATH = os.path.join(cls.tmp.name, "data", "tasks.json")
        cls.httpd = server.make_server(0)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    def call(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        c.request(method, path, json.dumps(body) if body is not None else None, headers)
        r = c.getresponse()
        raw = r.read()
        c.close()
        return r.status, (json.loads(raw) if raw else None)

    def good(self, **kw):
        d = {"title": "Fix bug", "tag": "Bugfix", "minutes": 45, "date": "2026-10-29"}
        d.update(kw)
        return d

    def test_index(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/")
        r = c.getresponse()
        self.assertEqual(r.status, 200)
        self.assertIn(b"DevPulse", r.read())

    def test_crud_and_persistence(self):
        s, t = self.call("POST", "/api/tasks", self.good())
        self.assertEqual(s, 201)
        self.assertEqual(t["tag"], "bugfix")
        self.assertFalse(t["done"])
        with open(server.DATA_PATH, encoding="utf-8") as f:
            self.assertIn(t["id"], [x["id"] for x in json.load(f)])

        s, t2 = self.call("PATCH", "/api/tasks/" + t["id"], {"done": True})
        self.assertEqual((s, t2["done"]), (200, True))

        s, tasks = self.call("GET", "/api/tasks?from=2026-10-29&to=2026-10-29")
        self.assertIn(t["id"], [x["id"] for x in tasks])
        s, tasks = self.call("GET", "/api/tasks?from=2026-11-01")
        self.assertNotIn(t["id"], [x["id"] for x in tasks])

        self.assertEqual(self.call("DELETE", "/api/tasks/" + t["id"])[0], 204)
        self.assertEqual(self.call("DELETE", "/api/tasks/" + t["id"])[0], 404)

    def test_default_tag(self):
        s, t = self.call("POST", "/api/tasks", self.good(tag="  "))
        self.assertEqual((s, t["tag"]), (201, "general"))

    def test_validation(self):
        for bad in (
            self.good(title=""),
            self.good(title="x" * 201),
            self.good(minutes=0),
            self.good(minutes=1441),
            self.good(minutes="5"),
            self.good(minutes=True),
            self.good(date="2026-13-40"),
            self.good(date="today"),
            self.good(tag="a,b"),
            self.good(tag="x" * 31),
        ):
            self.assertEqual(self.call("POST", "/api/tasks", bad)[0], 400, bad)

    def test_not_found_and_bad_patch(self):
        self.assertEqual(self.call("PATCH", "/api/tasks/" + "0" * 32, {"done": True})[0], 404)
        self.assertEqual(self.call("GET", "/nope")[0], 404)
        _, t = self.call("POST", "/api/tasks", self.good())
        self.assertEqual(self.call("PATCH", "/api/tasks/" + t["id"], {"done": "yes"})[0], 400)

    def test_patch_edit_fields(self):
        _, t = self.call("POST", "/api/tasks", self.good())
        path = "/api/tasks/" + t["id"]
        s, t2 = self.call("PATCH", path, {"title": " New ", "tag": "Docs", "minutes": 90})
        self.assertEqual(s, 200)
        self.assertEqual((t2["title"], t2["tag"], t2["minutes"], t2["done"]), ("New", "docs", 90, False))
        for bad in ({}, {"title": ""}, {"minutes": 0}, {"minutes": True}, {"tag": "a,b"}):
            self.assertEqual(self.call("PATCH", path, bad)[0], 400, bad)
        _, tasks = self.call("GET", "/api/tasks")
        self.assertEqual(next(x for x in tasks if x["id"] == t["id"])["title"], "New")

    def test_corrupt_file_is_kept(self):
        os.makedirs(os.path.dirname(server.DATA_PATH), exist_ok=True)
        with open(server.DATA_PATH, "w") as f:
            f.write("{not json")
        s, tasks = self.call("GET", "/api/tasks")
        self.assertEqual((s, tasks), (200, []))
        self.assertTrue(os.path.exists(server.DATA_PATH + ".bad"))


if __name__ == "__main__":
    unittest.main()
