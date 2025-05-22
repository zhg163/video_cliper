# -*- coding: utf-8 -*-

# Author : 'hxc'

# Time: 2025/5/13 07:54

# File_name: 'multi_llm.py'

"""
Describe: this is a demo!
"""

from dashscope import MultiModalConversation



def get_ts_from_llm(text,local_path):

    # 将xxxx/test.mp4替换为你本地视频的绝对路径
    # local_path = '/Users/huangxiancun/PycharmProjects/projects/hxc_nlp/video_cliper/data/331_1746806973.mp4'
    video_path = f"file://{local_path}"
    print(video_path)
    messages = [{'role': 'system',
                 'content': [{'text': 'You are a helpful assistant.'}]},
                {'role': 'user',
                 # fps参数控制视频抽帧数量，表示每隔1/fps 秒抽取一帧
                 'content': [{'video': video_path, "fps": 2},
                             {'text': text}]}]
    response = MultiModalConversation.call(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
        # api_key="sk-eb81b2ea880a441b8bf8b22bbc34f2fb",
        api_key='sk-06e0ddb0a8374fcfaac5fbc727a36ae8',
        model='qwen2.5-vl-72b-instruct',
        messages=messages)


    print(response)

    res = response["output"]["choices"][0]["message"].content[0]["text"]

    return res


if __name__ == "__main__":
    local_path = "/Users/huangxiancun/PycharmProjects/projects/hxc_nlp/video_cliper/data/视频高光时刻项目 2025-05-05 12.02.42.mp4"

    get_ts_from_llm(text="帮我剪辑有关打斗的片段",local_path=local_path)