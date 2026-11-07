"""首页右下角状态面板的数据接口 /api/status。"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from app import create_app
from src.api.status import clear_cache
from src.db import get_db


class SystemStatusTest(unittest.TestCase):
    def setUp(self):
        clear_cache()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": os.path.join(self.temp_dir.name, "test.db"),
        })
        self.client = self.app.test_client()

    def tearDown(self):
        clear_cache()
        self.temp_dir.cleanup()

    def status(self):
        clear_cache()
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def add_logs(self, ok, failed):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.app.app_context():
            db = get_db()
            rows = [(200, 800)] * ok + [(400, 300)] * failed
            db.executemany(
                "INSERT INTO request_logs(user_id, platform, path, status_code, duration_ms, created_at) VALUES (1, '抖音', '/api/parse', ?, ?, ?)",
                [(code, ms, now) for code, ms in rows],
            )
            db.commit()

    def test_healthy_system(self):
        data = self.status()
        self.assertEqual(data["overall"], "ok")
        self.assertTrue(data["api_enabled"])
        self.assertEqual(data["platforms_available"], data["platforms_total"])
        self.assertIsNone(data["success_rate_24h"])  # 样本不足时不给出成功率
        self.assertNotIn("calls", data)

    def test_success_rate_and_latency(self):
        self.add_logs(ok=18, failed=2)
        data = self.status()
        self.assertEqual(data["success_rate_24h"], 90.0)
        self.assertEqual(data["avg_ms_24h"], 800)
        self.assertEqual(data["overall"], "ok")

    def test_low_success_rate_is_degraded(self):
        self.add_logs(ok=5, failed=15)
        self.assertEqual(self.status()["overall"], "degraded")

    def test_disabled_platform_is_degraded(self):
        with self.app.app_context():
            db = get_db()
            db.execute("INSERT INTO platform_settings(platform, enabled) VALUES ('抖音', 0)")
            db.commit()
        data = self.status()
        self.assertEqual(data["overall"], "degraded")
        self.assertEqual(data["platforms_available"], data["platforms_total"] - 1)

    def test_api_switched_off_is_down(self):
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE system_settings SET value='0' WHERE key='global_api_enabled'")
            db.commit()
        data = self.status()
        self.assertEqual(data["overall"], "down")
        self.assertFalse(data["parser_enabled"])

    def test_old_logs_are_ignored(self):
        old = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(timespec="seconds")
        with self.app.app_context():
            db = get_db()
            db.executemany(
                "INSERT INTO request_logs(user_id, platform, path, status_code, duration_ms, created_at) VALUES (1, '抖音', '/api/parse', 400, 100, ?)",
                [(old,)] * 20,
            )
            db.commit()
        data = self.status()
        self.assertIsNone(data["success_rate_24h"])
        self.assertEqual(data["overall"], "ok")


if __name__ == "__main__":
    unittest.main()
