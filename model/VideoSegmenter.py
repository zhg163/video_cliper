# -*- coding: utf-8 -*-

# Author : 'hxc'

# Time: 2025/5/17 10:49

# File_name: 'VideoSegmenter.py'

"""
Describe: this is a demo!
"""
import time
import google.generativeai as genai
from dashscope import MultiModalConversation
import cv2
import os
from moviepy.editor import VideoFileClip, concatenate_videoclips
import numpy as np
from PIL import Image


# 配置 Gemini
def configure_gemini(api_key):
    genai.configure(api_key=api_key)


API_KEY = "AIzaSyDjp0jIUEiQ1VYTQZLzoWqHKITNEpLVlvM"
configure_gemini(API_KEY)
class VideoSegmenter:
    def __init__(self, video_path):
        self.video_path = video_path
        self.clip = VideoFileClip(video_path)
        self.fps = self.clip.fps
        self.duration = self.clip.duration

    def extract_keyframes(self, interval=5):
        """提取关键帧（带时间戳）"""
        frames = []
        timestamps = []

        for t in np.arange(0, self.duration, interval):
            frame = self.clip.get_frame(t)
            frames.append(Image.fromarray(frame))
            timestamps.append(t)

        return frames, timestamps

    def analyze_frames(self, frames, user_prompt):
        """使用 Gemini 分析帧是否匹配用户描述"""
        model = genai.GenerativeModel('gemini-1.5-flash')
        matches = []

        prompt = f"""
        当前用户需要寻找的视频片段描述：'{user_prompt}'
        请判断当前画面是否匹配该描述，只需回复 YES 或 NO。
        """

        for img in frames:
            response = model.generate_content([prompt, img])

            matches.append("YES" in response.text.upper())
            time.sleep(20)

        return matches

    import os
    import dashscope
    from dashscope import MultiModalConversation
    from PIL import Image

    def analyze_frames_aliyun(self, frames, user_prompt):

            matches = []
            prompt = f"""
                  当前用户需要寻找的视频片段描述：'{user_prompt}'
                  请判断当前画面是否匹配该描述，只需回复 YES 或 NO。
                  """

            for img in frames:
                img_path = "temp_frame.jpg"
                img.save(img_path)

                try:
                    response = MultiModalConversation.call(
                        model="qwen-vl-plus",
                        api_key='sk-06e0ddb0a8374fcfaac5fbc727a36ae8',
                        messages=[{
                            "role": "user",
                            "content": [
                                {"image": img_path},
                                {"text": prompt}
                            ]
                        }]
                    )
                    answer = response["output"]["choices"][0]["message"]["content"][0]['text']
                    print(answer)
                    matches.append("YES" in answer.upper())
                except Exception as e:
                    print(f"Error: {e}")
                    matches.append(False)
                finally:
                    time.sleep(1)  # 控制调用频率
                    if os.path.exists(img_path):
                        os.remove(img_path)

            return matches

    def find_relevant_segments(self, user_prompt, interval=5):
        """找到所有相关片段的时间区间"""
        frames, timestamps = self.extract_keyframes(interval)
        # matches = self.analyze_frames(frames, user_prompt)
        matches = self.analyze_frames_aliyun(frames, user_prompt)

        print("match:",matches)

        segments = []
        in_segment = False
        start_time = 0

        print("时间区间：",timestamps)

        for i, (match, t) in enumerate(zip(matches, timestamps)):
            if match and not in_segment:
                start_time = t
                in_segment = True
            elif not match and in_segment:
                # end_time = timestamps[i+1] if i > 0 else t
                # start_time =  timestamps[i-2] if i > 0 else t

                segments.append(( timestamps[i-2] if i > 0 else t, start_time))
                segments.append((start_time, timestamps[i+1] if i > 0 else t))
                in_segment = False

        if in_segment:  # 处理最后一个片段
            segments.append((start_time, self.duration))

        return segments

    def compile_highlight_video(self, segments, output_path="highlight.mp4"):
        """编译高光片段视频"""
        subclips = []
        for start, end in segments:
            subclip = self.clip.subclip(start, end)
            subclips.append(subclip)

        if not subclips:
            raise ValueError("没有找到匹配的片段")

        final_clip = concatenate_videoclips(subclips)
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        return output_path


if __name__ == "__main__":
    # 配置

    VIDEO_PATH = "./data/视频高光时刻项目 2025-05-05 12.02.42.mp4"  # 替换为你的视频路径
    OUTPUT_PATH = "highlight_output.mp4"

    configure_gemini(API_KEY)

    # 用户输入描述
    user_prompt = "打斗的画面"

    # 处理视频
    segmenter = VideoSegmenter(VIDEO_PATH)

    print("正在分析视频...")
    relevant_segments = segmenter.find_relevant_segments(user_prompt, interval=3)  # 每3秒检测一帧
    relevant_segments_new = []
    if not relevant_segments:
        print("未找到匹配片段")
    else:
        print(f"找到 {len(relevant_segments)} 个匹配片段：")
        for i, (start, end) in enumerate(relevant_segments):
            if start !=end and float(end) > float(start):
                relevant_segments_new.append((start, end))
                print(f"片段 {i + 1}: {start:.1f}s - {end:.1f}s")

        print("\n正在生成高光视频...")
        output_path = segmenter.compile_highlight_video(relevant_segments_new, OUTPUT_PATH)
        print(f"已生成高光视频: {output_path}")
