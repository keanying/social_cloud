"""品牌迁移：上游默认署名自动改为社媒云，管理员自定义的值不受影响。"""
import os
import tempfile
import unittest

from app import create_app
from src.db import get_db, init_db, setting


class BrandMigrationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": os.path.join(self.temp_dir.name, "test.db"),
        })

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_legacy_defaults_migrate_but_custom_values_stay(self):
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE system_settings SET value='ucmao' WHERE key='api_tip_author'")
            db.execute("UPDATE system_settings SET value='https://github.com/ucmao/media-parser' WHERE key='api_tip_website'")
            db.execute("UPDATE system_settings SET value='我们自己的提示' WHERE key='api_tip_notice'")
            db.commit()
            init_db()
            self.assertEqual(setting("api_tip_author"), "社媒云")
            self.assertEqual(setting("api_tip_website"), "")
            self.assertEqual(setting("api_tip_notice"), "我们自己的提示")


if __name__ == "__main__":
    unittest.main()
