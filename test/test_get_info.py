# -*- coding: utf-8 -*-

# Author : 'hxc'

# Time: 2025/5/22 22:24

# File_name: 'test_get_info.py'

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
        url = "http://server.lovedraw.cn:18622/video_cliper/get_info"

        input = {"origin_video_uid":"JQ6b6ede29-e732-4e63-a0b7-312ca6d4160c"
                 }

        headers = {
            'Content-Type': 'application/json'
        }

        res = requests.post(url, json=input, headers=headers)
        print(res)
        print(json.dumps(res.json(), indent=4, ensure_ascii=False,sort_keys=False))
        print(time.time() - t)

if __name__ == '__main__':
    unittest.main()