# -*- coding: utf-8 -*-

# Author : 'hxc'

# Time: 2025/5/20 21:16

# File_name: 'run_video_cliper_app.py'

"""
Describe: this is a demo!
"""

import time
import os
from datetime import datetime
import logging
import requests
import uvicorn
import json
import uuid
import shutil
from loguru import logger
from fastapi import FastAPI,BackgroundTasks
from fastapi.params import Body,Query
from os import path
from fastapi.responses import FileResponse
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from model.VideoSegmenter import VideoSegmenter


# 导入日志配置文件
log_file_path = path.join(path.dirname(path.abspath(__file__)), "configs/logging.conf")
logging.config.fileConfig(log_file_path)
# 创建日志对象
logger = logging.getLogger()
loggerInfo = logging.getLogger("TimeInfoLogger")
Consolelogger = logging.getLogger("ConsoleLogger")


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:18622"],  # Allow requests from this origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info('视频剪辑后端服务初始化成功！！！')
UPLOAD_DIR = "uploads"  # 上传文件保存目录
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 1024 * 1024 * 500  # 500MB 限制




def process_data_in_background(origin_video,video_cut_info):
    """后台处理剪辑"""


    jq_folder = video_cut_info["video_cut_path"]
    interval = video_cut_info["interval"]
    user_prompt = video_cut_info["user_prompt"]
    video_num = video_cut_info["video_num"]
    status = video_cut_info["status"]
    msg = video_cut_info["msg"]



    logger.info("进行裁剪:{}".format(video_num))
    logger.info("jq_folder:{}".format(jq_folder))
    logger.info("user_prompt:{}".format(user_prompt))
    logger.info("interval:{}".format(interval))
    logger.info("status:{}".format(status))
    logger.info("msg:{}".format(msg))

    VIDEO_PATH = origin_video # 替换为你的视频路径
    logger.info("origin path:{}".format(VIDEO_PATH))

    OUTPUT_PATH =  os.path.join(jq_folder, f"{video_num}_clip.mp4")

    # 处理视频
    segmenter = VideoSegmenter(VIDEO_PATH)

    logger.info("正在分析视频...")
    relevant_segments = segmenter.find_relevant_segments(user_prompt, interval=3)  # 每3秒检测一帧
    relevant_segments_new = []
    if not relevant_segments:
        logger.info("未找到匹配片段")
        video_cut_info['status'] = '3'
        video_cut_info['msg'] = "未找到匹配片段"

    else:
        logger.info(f"找到 {len(relevant_segments)} 个匹配片段：")
        for i, (start, end) in enumerate(relevant_segments):
            if start != end and float(end) > float(start):
                relevant_segments_new.append((start, end))
                logger.info(f"片段 {i + 1}: {start:.1f}s - {end:.1f}s")

        logger.info("\n正在生成高光视频...")
        output_path = segmenter.compile_highlight_video(relevant_segments_new, OUTPUT_PATH)
        logger.info(f"已生成高光视频: {output_path}")

        video_cut_info['status'] = '2'
        video_cut_info['msg'] = "裁剪完成"

    # 保存视频信息到cut_output文件夹
    json_path = os.path.join(jq_folder, "video_cut_info.json")
    with open(json_path, "w", encoding='utf-8') as json_file:
        json.dump(video_cut_info, json_file, ensure_ascii=False, indent=4)

    logger.info("完成裁剪。")

app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")

@app.post('/video_cliper/upload_video')
async def upload_video(file: UploadFile = File(...)):

    # 验证文件大小
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件太大. 最大允许 {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )

    # 生成JQ编号和安全的文件名
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    enquiry_num = 'JQ' + str(uuid.uuid4())

    # 创建JQ编号的文件夹
    jq_folder = os.path.join(UPLOAD_DIR, enquiry_num)
    os.makedirs(jq_folder, exist_ok=True)

    # 生成安全的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(file.filename)[1]  # 获取文件扩展名
    safe_filename = f"video_origin_{timestamp}{file_ext}"
    save_path = os.path.join(jq_folder, safe_filename)

    try:
        # 保存文件
        with open(save_path, "wb") as buffer:
            # 分块读取和写入，避免内存问题
            while chunk := await file.read(1024 * 1024):  # 每次读取1MB
                buffer.write(chunk)

        # 创建video_info字典
        video_info = {
            "enquiry_num": enquiry_num,
            "video_name": safe_filename,
            "video_path": save_path,
            "create_time": current_time

        }
        # 将video_info保存为JSON文件
        json_path = os.path.join(jq_folder, "video_info.json")
        with open(json_path, "w",encoding="utf-8") as json_file:
            json.dump(video_info, json_file,ensure_ascii=False, indent=4)

        result = {"enquiry_num": enquiry_num}
        # 返回成功响应
        return {"success": True, "code": 200, "msg": "视频上传成功", "data": result}
    except Exception as e:
        # 如果出错，删除可能已创建的文件和文件夹
        if os.path.exists(save_path):
            os.remove(save_path)
        if os.path.exists(jq_folder):
            try:
                os.rmdir(jq_folder)  # 尝试删除空文件夹
            except OSError:
                pass  # 文件夹非空，暂时保留

        return {"success": False, "code": 500, "msg": "视频上传失败：" + str(e), "data": {}}


@app.post('/video_cliper/start_video_cliper')
async def start_video_cliper(
        background_tasks: BackgroundTasks,
        enquiry_num: str = Body(embed=True, default="", description="剪辑编号"),
        interval: int = Body(embed=True, default=3, description="每多少秒检测一帧"),
        user_prompt: str = Body(embed=True, default="", description="用户提示词"),
):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        video_info_path = base_path + f"/uploads/{enquiry_num}/video_info.json"
        video_num = 'Video-' + str(uuid.uuid4())

        # 加载视频信息
        with open(video_info_path, 'r', encoding='utf-8') as f:
            video_info = json.load(f)

        origin_video = video_info['video_path']

        # 创建cut_output文件夹
        cut_output_folder = os.path.join(UPLOAD_DIR, enquiry_num, "cut_output")
        logger.info(f"cut_output_folder: {cut_output_folder}")
        os.makedirs(cut_output_folder, exist_ok=True)

        # 创建视频UUID子文件夹
        video_uuid_folder = os.path.join(cut_output_folder, video_num)
        os.makedirs(video_uuid_folder, exist_ok=True)  # 存放裁剪的视频

        video_cut_info = {
            "video_num":video_num,
            "video_cut_path": video_uuid_folder,
            "interval": interval,
            "user_prompt": user_prompt,
            "status": "1",
            "msg": "裁剪中"
        }

        # 保存视频信息到cut_output文件夹
        json_path = os.path.join(video_uuid_folder, "video_cut_info.json")
        with open(json_path, "w", encoding='utf-8') as json_file:
            json.dump(video_cut_info, json_file, ensure_ascii=False, indent=4)

        # 后台处理
        background_tasks.add_task(process_data_in_background,origin_video, video_cut_info)

        result = {"video_num": video_num}
        return {"success": True, "code": 200, "msg": "已受理", "data": result}

    except Exception as e:
        return {"success": False, "code": 500, "msg": str(e), "data": {}}


@app.post("/video_cliper/download_video")
async def download_video(
        origin_video_uid: str = Body(...,embed=True, description="原视频uid"),
        cut_video_uid: str = Body(...,embed=True, description="裁剪视频uid"),
):
    try:
        video_path = f"uploads/{origin_video_uid}/cut_output/{cut_video_uid}/{cut_video_uid}_clip.mp4"

        # Add debug logging
        logger.info(f"Looking for video at: {video_path}")

        # Check if path exists and is a file
        if not os.path.exists(video_path):
            return {"success": False, "code": 404, "msg": "视频不存在", "data": {}}

        if not os.path.isfile(video_path):
            return {"success": False, "code": 400, "msg": "路径不是文件", "data": {}}

        # Verify file is readable
        if not os.access(video_path, os.R_OK):
            return {"success": False, "code": 403, "msg": "无文件读取权限", "data": {}}

        logger.info(f"返回下载视频: {video_path}")
        return FileResponse(
            video_path,
            media_type="video/mp4",
            filename=f"{cut_video_uid}_clip.mp4"
        )
    except Exception as e:
        logger.error(f"下载视频出错: {str(e)}")
        return {"success": False, "code": 500, "msg": str(e), "data": {}}


@app.post("/video_cliper/get_info")
async def get_info(
        origin_video_uid: str = Body(...,embed=True, description="原视频uid")
):
    try:

        base_url = "https://server.lovedraw.cn"
        base_path = os.path.dirname(os.path.abspath(__file__))
        origin_path = f"uploads/{origin_video_uid}/video_info.json"
        cut_path = f"uploads/{origin_video_uid}/cut_output"

        # 加载视频信息
        with open(origin_path, 'r') as f:
            video_info = json.load(f)
            video_path_new = base_url + f"{base_path}/" +video_info['video_path']
            video_info['video_path'] = video_path_new

        logger.info(video_info)

        cut_history = {}
        cut_fold = os.listdir(cut_path)

        for i in cut_fold:
            cut_path_ = cut_path + f"/{i}/video_cut_info.json"

            with open(cut_path_, 'r') as f:
                cut_video_info = json.load(f)

                logger.info(cut_video_info['video_cut_path'])
                cut_video_path = base_url + f"{base_path}/" + cut_video_info['video_cut_path'] + f"/{i}_clip.mp4"
                cut_video_info['video_cut_path'] = cut_video_path
            cut_history[i] = cut_video_info

            logger.info(cut_video_info)

        video_info['cut_history'] = cut_history

        return {"success": True, "code": 200, "data": video_info}

    except Exception as e:
        logger.error(f"获取裁剪信息出错: {str(e)}")
        return {"success": False, "code": 500, "msg": str(e), "data": {}}




@app.post("/video_cliper/del_video")
async def del_video(
        origin_video_uid: str = Body(...,embed=True, description="原视频uid")

):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        origin_path =  f"{base_path}/uploads/{origin_video_uid}"
        logger.info(f"视频路径: {origin_path}")
        if os.path.exists(origin_path):
            shutil.rmtree(origin_path)

            return {"success": True, "code": 200, "msg": f"已删除: {origin_path}"}
        else:
            return {"success": True, "code": 200, "msg": f"路径不存在: {origin_path}"}


    except Exception as e:
        logger.error(f"获取裁剪信息出错: {str(e)}")
        return {"success": False, "code": 500, "msg": str(e)}









if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=18622,
        # workers=2,        # 进程数（通常设为 CPU 核心数）
        # access_log=False
    )
