# -*- coding: utf-8 -*-

# Author : 'hxc'

# Time: 2025/5/22 12:01

# File_name: 'test_download_video.py'

"""
Describe: this is a demo!
"""




import time
import unittest
import requests
import json


class TestModelPredict(unittest.TestCase):

    def testModelPredict(self):
        """
        测试 模型预测
        :return:
        """
        t = time.time()
        url = "http://server.lovedraw.cn:18622/video_cliper/download_video"

        input = {"origin_video_uid":"JQ6b6ede29-e732-4e63-a0b7-312ca6d4160c",
                 "cut_video_uid": "Video-6d3b4b26-de1f-49f9-932c-616ab932092a"
                 }

        headers = {
            'Content-Type': 'application/json'
        }

        res = requests.post(url, json=input, headers=headers)
        print(res.status_code)

        if res.status_code == 200:

            content_type = res.headers.get("Content-Type", "")

            # Check if response is actually a video
            if "video/mp4" in content_type:
                with open("test_download.mp4", "wb") as f:
                    f.write(res.content)
                print("Download successful!")
            else:
                # Handle JSON error
                error_data = res.json()
                print(f"Server error: {error_data}")

        else:
            print(f"Test failed: {res.json()}")

if __name__ == '__main__':
    unittest.main()