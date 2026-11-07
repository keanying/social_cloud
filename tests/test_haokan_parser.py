import json
import unittest
from unittest.mock import Mock, patch

from src.parsers.haokan_parser import HaokanParser
from utils.web_fetcher import UrlParser


class HaokanParserTest(unittest.TestCase):
    def test_parses_window_json_data(self):
        json_data_payload = {
            "data": {
                "title": "测试好看视频标题",
                "videoInfo": {
                    "title": "测试好看视频标题",
                    "posterImage": "https://image.example.com/poster.jpg",
                    "clarityArr": [
                        {"rank": 1, "url": "https://video.example.com/480p.mp4"},
                        {"rank": 3, "url": "https://video.example.com/1080p.mp4"},
                        {"rank": 2, "url": "https://video.example.com/720p.mp4"}
                    ]
                },
                "author": {
                    "name": "测试作者",
                    "uk": "123456",
                    "icon": "https://image.example.com/avatar.jpg"
                }
            }
        }
        html_page = (
            '<html><head>'
            f'<script>window.jsonData = {json.dumps(json_data_payload)};</script>'
            '</head><body></body></html>'
        )
        response = Mock(status_code=200, content=html_page.encode("utf-8"))

        with patch("requests.Session.get", return_value=response):
            parser = HaokanParser("https://mbd.baidu.com/newspage/data/videoshare?nid=sv_123456")

        self.assertEqual(parser.get_title_content(), "测试好看视频标题")
        self.assertEqual(parser.get_real_video_url(), "https://video.example.com/1080p.mp4")
        self.assertEqual(parser.get_cover_photo_url(), "https://image.example.com/poster.jpg")
        self.assertEqual(parser.get_author_info()["nickname"], "测试作者")
        self.assertEqual(parser.get_author_info()["author_id"], "123456")

    def test_url_parser_extracts_nid_and_sign(self):
        url = "https://mbd.baidu.com/newspage/data/videoshare?nid=sv_10423411367049244882&noise=123"
        extracted = UrlParser.extract_video_address(url)
        self.assertEqual(extracted, "https://mbd.baidu.com/newspage/data/videoshare?nid=sv_10423411367049244882")


if __name__ == "__main__":
    unittest.main()
