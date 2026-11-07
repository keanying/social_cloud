import unittest
from unittest.mock import Mock, patch

from src.parsers.pipixia_parser import PipixiaParser


class PipixiaParserTest(unittest.TestCase):
    @patch("src.parsers.pipixia_parser.random.choice", return_value="test-agent")
    def test_falls_back_to_share_page_title_and_extracts_author(self, _user_agent):
        redirect = Mock(headers={"location": "https://h5.pipix.com/ppx/item/123"})
        api_response = Mock()
        api_response.raise_for_status.return_value = None
        api_response.json.return_value = {
            "data": {"cell_comments": [{"comment_info": {"item": {
                "content": "",
                "author": {
                    "id": 42,
                    "name": "测试作者",
                    "avatar": {"download_list": [{"url": "https://image.example.com/avatar.jpg"}]},
                },
            }}}]}
        }
        page = Mock(text='<meta property="og:title" content="测试皮皮虾作品 - 皮皮虾">')
        page.raise_for_status.return_value = None

        with patch("requests.Session.get", side_effect=[redirect, api_response, page]):
            parser = PipixiaParser("https://h5.pipix.com/s/share-id/")

        self.assertEqual(parser.get_title_content(), "测试皮皮虾作品")
        self.assertEqual(
            parser.get_author_info(),
            {"nickname": "测试作者", "author_id": "42", "avatar": "https://image.example.com/avatar.jpg"},
        )

    def test_extracts_from_embedded_h5_script(self):
        h5_script = (
            '%7B%22sessionConfig%22%3A%7B%22groupId%22%3A%22123%22%7D%2C'
            '%22seoTDK%22%3A%7B%22title%22%3A%22皮皮虾图文作品%20-%20皮皮虾%22%7D%2C'
            '%22ppxItemDetail%22%3A%7B%22item%22%3A%7B'
            '%22content%22%3A%22测试图文内容%22%2C'
            '%22video%22%3A%7B%22video_download%22%3A%7B%22url_list%22%3A%5B%7B%22url%22%3A%22https%3A%2F%2Fvideo.example.com%2Fppx.mp4%22%7D%5D%7D%7D%2C'
            '%22cover%22%3A%7B%22url_list%22%3A%5B%7B%22url%22%3A%22https%3A%2F%2Fimage.example.com%2Fcover.jpg%22%7D%5D%7D%2C'
            '%22note%22%3A%7B%22multi_image%22%3A%5B%7B%22url_list%22%3A%5B%7B%22url%22%3A%22https%3A%2F%2Fimage.example.com%2F1.jpg%22%7D%5D%7D%5D%7D%2C'
            '%22author%22%3A%7B%22id%22%3A999%2C%22name%22%3A%22作者%22%2C%22avatar%22%3A%7B%22url_list%22%3A%5B%7B%22url%22%3A%22https%3A%2F%2Fimage.example.com%2Favatar.jpg%22%7D%5D%7D%7D'
            '%7D%7D%7D'
        )
        html = f'<html><head><script>{h5_script}</script></head><body></body></html>'
        page = Mock(text=html, headers={})
        page.raise_for_status.return_value = None

        with patch("requests.Session.get", return_value=page):
            parser = PipixiaParser("https://h5.pipix.com/ppx/item/123")

        self.assertEqual(parser.get_title_content(), "皮皮虾图文作品")
        self.assertEqual(parser.get_description(), "测试图文内容")
        self.assertEqual(parser.get_real_video_url(), "https://video.example.com/ppx.mp4")
        self.assertEqual(parser.get_cover_photo_url(), "https://image.example.com/cover.jpg")
        self.assertEqual(parser.get_image_list(), ["https://image.example.com/1.jpg"])
        self.assertEqual(parser.get_author_info(), {"nickname": "作者", "author_id": "999", "avatar": "https://image.example.com/avatar.jpg"})

    def test_returns_empty_data_when_redirect_has_no_item_id(self):
        response = Mock(headers={"location": ""})
        with patch("requests.Session.get", return_value=response) as get:
            parser = PipixiaParser("https://h5.pipix.com/s/share-id/")

        get.assert_called_once()
        self.assertEqual(parser.data, {})


if __name__ == "__main__":
    unittest.main()
