# -*- coding: utf-8 -*-

# Author : 'hxc'

# Time: 2025/5/13 07:59

# File_name: 'llm.py'

"""
Describe: this is a demo!
"""




from openai import OpenAI

client = OpenAI(api_key="sk-a7eb4f75add447a688c4ee276e29b6b1", base_url="https://api.deepseek.com")
# client = OpenAI(api_key="sk-06e0ddb0a8374fcfaac5fbc727a36ae8", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")



def llm_response(query,response_format):
    """

    :param query:
    :param response_format: text  json_object
    :return:
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        # model = "deepseek-reasoner",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": query},
        ],
        response_format={
            'type': response_format
        },
        temperature=0,
        top_p=1,
        seed=42,
        stream=False
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    r = llm_response(query="你是谁",response_format='text')
    print(r)