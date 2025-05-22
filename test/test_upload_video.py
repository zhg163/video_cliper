#!D:/workplace/python
# -*- coding: utf-8 -*-
# Copyright ©  版权所有
# @File  : test_upload_video.py
# @Author:
# @Date  : 2025/4/15 16:03
"""
Describe: this is a demo!
"""

import os
import time
import unittest
import requests
import json


class TestUploadVideo(unittest.TestCase):

    def testUploadVideo(self):
        """
        测试 模型预测
        :return:
        """
        t = time.time()
        url = "http://server.lovedraw.cn:18622/video_cliper/upload_video"

        file_path = "../data/331_1746806973.mp4"


        with open(file_path, "rb") as f:
            file_content = f.read()

        files = {"file": (file_path, file_content, "video/mp4")}

        res = requests.post(url, files=files)
        print(res)
        print(json.dumps(res.json(), indent=4, ensure_ascii=False,sort_keys=False))
        print(time.time() - t)

if __name__ == '__main__':
    unittest.main()