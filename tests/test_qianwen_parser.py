import unittest
from unittest.mock import Mock, patch

from src.parsers.qianwen_parser import QianwenParser


class QianwenParserTest(unittest.TestCase):
    def test_parses_qianwen_share_props(self):
        page_html = """
        <!DOCTYPE html>
        <html>
        <head><title>千问</title></head>
        <body>
        <script>
        window.__INITIAL_PROPS__ = {
            "initialData": {
                "data": {
                    "shareId": "ZeeOedXncnGlElkluRMA",
                    "title": "给右边男生的黑色卫衣换成灰色",
                    "creator": {
                        "nick": "Qwen5361",
                        "authorId": "OjTAcGHgZgyeCwY4jeMDuH9Je4J92YdmlmTiIxK0cRWKzw==",
                        "avatar": "https://gw.alicdn.com/avatar.png"
                    },
                    "images": [
                        {
                            "downloadUrl": "https://quark-aistudio-cdn.quark.cn/test1.png",
                            "url": "https://quark-aistudio-cdn.quark.cn/test1_preview.png"
                        }
                    ]
                }
            }
        };
        </script>
        </body>
        </html>
        """

        page_resp = Mock()
        page_resp.raise_for_status.return_value = None
        page_resp.text = page_html

        url = "https://activity.qianwen.com/r/ai-studio-mobile/qwen-external-share?shareId=ZeeOedXncnGlElkluRMA"
        with patch("requests.Session.get", return_value=page_resp):
            parser = QianwenParser(url)

        self.assertEqual(parser.get_title_content(), "给右边男生的黑色卫衣换成灰色")
        self.assertIsNone(parser.get_cover_photo_url())
        self.assertEqual(parser.get_image_list(), ["https://quark-aistudio-cdn.quark.cn/test1_preview.png"])
        self.assertEqual(
            parser.get_author_info(),
            {
                "nickname": "Qwen5361",
                "author_id": "OjTAcGHgZgyeCwY4jeMDuH9Je4J92YdmlmTiIxK0cRWKzw==",
                "avatar": "https://gw.alicdn.com/avatar.png",
            },
        )

    def test_parses_qianwen_chat2_spa_api(self):
        api_data = {
            "code": 0,
            "msg": "success",
            "data": {
                "title": "图片人物美白处理",
                "session": {
                    "title": "修图建议：去旁人，亮肤色",
                    "record_list": [
                        {
                            "request_messages": [{"content": "将图中人物变白"}],
                            "response_messages": [
                                {
                                    "display_list": [
                                        {
                                            "image": [{"url": "https://workspace-zb-cdn.qianwen.com/test_output.png"}]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }
        api_resp = Mock()
        api_resp.status_code = 200
        api_resp.json.return_value = api_data

        url = "https://qianwen.my.cn/share/chat/84c5660504a44063bec11136615b9256"
        with patch("requests.Session.post", return_value=api_resp):
            parser = QianwenParser(url)

        self.assertEqual(parser.get_title_content(), "图片人物美白处理")
        self.assertIsNone(parser.get_cover_photo_url())
        self.assertEqual(parser.get_image_list(), ["https://workspace-zb-cdn.qianwen.com/test_output.png"])

    def test_invalid_url_handles_gracefully(self):
        parser = QianwenParser("https://activity.qianwen.com/invalid")
        self.assertEqual(parser.get_title_content(), "")
        self.assertIsNone(parser.get_real_video_url())
        self.assertEqual(parser.get_image_list(), [])
        self.assertIsNone(parser.get_cover_photo_url())
        self.assertIsNone(parser.get_author_info())


if __name__ == "__main__":
    unittest.main()
