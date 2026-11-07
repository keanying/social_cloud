import unittest
from unittest.mock import Mock, patch

from src.parsers.xiaoyunque_parser import XiaoyunqueParser
from utils.web_fetcher import UrlParser


class XiaoyunqueParserTest(unittest.TestCase):
    def test_maps_official_api_response(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "err_no": 0,
            "err_tips": "success",
            "data": {
                "page_info": {
                    "generate_page": {
                        "user_info": {
                            "nick_name": "测试作者",
                            "avatar_url": "https://image.example.com/avatar.jpg",
                        },
                        "item_info": {
                            "desc": "测试小云雀作品描述",
                            "image_info": [
                                {"image_url": "https://image.example.com/item1.png", "width": 1000, "height": 1000}
                            ],
                        },
                    }
                }
            },
        }
        url = "https://xiaoyunque.jianying.com/activities/pippit_share?artifact_id=12345&generate_id=abcde"

        with patch("requests.Session.post", return_value=response) as post:
            parser = XiaoyunqueParser(url)

        self.assertIsNone(parser.get_title_content())
        self.assertEqual(parser.get_description(), "测试小云雀作品描述")
        self.assertEqual(parser.get_image_list(), ["https://image.example.com/item1.png"])
        self.assertIsNone(parser.get_cover_photo_url())
        self.assertEqual(parser.get_author_info()["nickname"], "测试作者")
        self.assertEqual(
            post.call_args.kwargs["json"]["query_params"]["artifact_id"],
            "12345",
        )

    def test_inspiration_page_response(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "err_no": 0,
            "err_tips": "success",
            "data": {
                "page_info": {
                    "inspiration_page": {
                        "user_info": {
                            "nick_name": "茉莱",
                            "avatar_url": "https://p26-passport.byteacctimg.com/avatar.jpg",
                        },
                        "item_info": {
                            "title": "三角洲原图壁纸",
                            "desc": "壁纸生成",
                            "video_info": [
                                {"video_url": "https://v11-xyq-video.jianying.com/video.mp4"}
                            ],
                        },
                    }
                }
            },
        }
        url = "https://xiaoyunque.jianying.com/activities/pippit_share?inspiration_id=7684286783865146686"

        with patch("requests.Session.post", return_value=response):
            parser = XiaoyunqueParser(url)

        self.assertEqual(parser.get_title_content(), "三角洲原图壁纸")
        self.assertEqual(parser.get_description(), "壁纸生成")
        self.assertEqual(parser.get_real_video_url(), "https://v11-xyq-video.jianying.com/video.mp4")
        self.assertEqual(parser.get_author_info()["nickname"], "茉莱")

    def test_gugu_page_response(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "err_no": 0,
            "err_tips": "success",
            "data": {
                "page_info": {
                    "gugu_page": {
                        "current_index": 0,
                        "item_list": [
                            {
                                "title": "F级废物给鬼号脉",
                                "desc": "首映剧情",
                                "author_info": {
                                    "nick_name": "浅酱雨禾",
                                    "avatar_url": "https://avatar.example.com/qian.jpg",
                                },
                                "video_info": [
                                    {
                                        "video_url": "https://v11-xyq-video.jianying.com/gugu.mp4",
                                        "cover_url": "https://cover.example.com/gugu.jpg",
                                    }
                                ],
                            }
                        ],
                    }
                }
            },
        }
        url = "https://xiaoyunque.jianying.com/activities/pippit_share?gugu_id=12345"

        with patch("requests.Session.post", return_value=response):
            parser = XiaoyunqueParser(url)

        self.assertEqual(parser.get_title_content(), "F级废物给鬼号脉")
        self.assertEqual(parser.get_description(), "首映剧情")
        self.assertEqual(parser.get_real_video_url(), "https://v11-xyq-video.jianying.com/gugu.mp4")
        self.assertEqual(parser.get_cover_photo_url(), "https://cover.example.com/gugu.jpg")
        self.assertEqual(parser.get_author_info()["nickname"], "浅酱雨禾")

    def test_url_parser_recognizes_xiaoyunque(self):
        url = "https://xiaoyunque.jianying.com/s/z_7nWGLGruM/"
        self.assertEqual(UrlParser.get_platform(url), "小云雀AI")


if __name__ == "__main__":
    unittest.main()
