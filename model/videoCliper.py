# -*- coding: utf-8 -*-

# Author : 'hxc'

# Time: 2025/5/10 10:57

# File_name: 'videoCliper.py'

"""
Describe: this is a demo!
"""
import re
import numpy as np
import sys
import copy
import librosa
import logging
import argparse
import numpy as np
from moviepy.editor import *
import moviepy.editor as mpy
from moviepy.video.tools.subtitles import SubtitlesClip, TextClip
from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from funasr import AutoModel
from utils.subtitle_utils import generate_srt, generate_srt_clip
from utils.trans_utils import pre_proc, proc, write_state, load_state, proc_spk, convert_pcm_to_float

class VideoClipper():
    def __init__(self, funasr_model):
        logging.warning("Initializing VideoClipper.")
        self.funasr_model = funasr_model
        self.GLOBAL_COUNT = 0

    def recog(self, audio_input, sd_switch='no', state=None, hotwords="", output_dir=None):
        if state is None:
            state = {}
        sr, data = audio_input

        # Convert to float64 consistently (includes data type checking)
        data = convert_pcm_to_float(data)

        # assert sr == 16000, "16kHz sample rate required, {} given.".format(sr)
        if sr != 16000:  # resample with librosa
            data = librosa.resample(data, orig_sr=sr, target_sr=16000)
        if len(data.shape) == 2:  # multi-channel wav input
            logging.warning("Input wav shape: {}, only first channel reserved.".format(data.shape))
            data = data[:, 0]
        state['audio_input'] = (sr, data)
        if sd_switch == 'Yes':
            rec_result = self.funasr_model.generate(data,
                                                    return_spk_res=True,
                                                    return_raw_text=True,
                                                    is_final=True,
                                                    output_dir=output_dir,
                                                    hotword=hotwords,
                                                    pred_timestamp=self.lang == 'en',
                                                    en_post_proc=self.lang == 'en',
                                                    cache={})
            res_srt = generate_srt(rec_result[0]['sentence_info'])
            state['sd_sentences'] = rec_result[0]['sentence_info']
        else:
            rec_result = self.funasr_model.generate(data,
                                                    return_spk_res=False,
                                                    sentence_timestamp=True,
                                                    return_raw_text=True,
                                                    is_final=True,
                                                    hotword=hotwords,
                                                    output_dir=output_dir,
                                                    pred_timestamp=self.lang == 'en',
                                                    en_post_proc=self.lang == 'en',
                                                    cache={})
            res_srt = generate_srt(rec_result[0]['sentence_info'])
        state['recog_res_raw'] = rec_result[0]['raw_text']
        state['timestamp'] = rec_result[0]['timestamp']
        state['sentences'] = rec_result[0]['sentence_info']
        res_text = rec_result[0]['text']
        return res_text, res_srt, state

    def _concat_clips(self, data, all_ts, start_ost, end_ost, sentences,sr):
        res_audio = np.array([], dtype=np.float64)
        clip_srt = ""
        srt_index = 0
        start_end_info = []

        for start, end in all_ts:
            start = max(0, start + start_ost * 16)
            end = min(len(data), end + end_ost * 16)
            res_audio = np.concatenate([res_audio, data[start:end]])
            start_end_info.append(f"from {start / 16000:.2f}s to {end / 16000:.2f}s")

            # 生成 SRT
            srt_clip, _, srt_index = generate_srt_clip(
                sentences, start / 16000.0, end / 16000.0, begin_index=srt_index
            )
            clip_srt += srt_clip

        message = f"{len(all_ts)} segments found: " + ", ".join(start_end_info)
        return (sr, res_audio), message, clip_srt

    def clip(self, dest_text, start_ost, end_ost, state, dest_spk=None, output_dir=None, timestamp_list=None):
        # get from state
        audio_input = state['audio_input']
        recog_res_raw = state['recog_res_raw']
        timestamp = state['timestamp']
        sentences = state['sentences']
        sr, data = audio_input
        data = data.astype(np.float64)


        if timestamp_list is None:
            all_ts = []
            if dest_spk is None or dest_spk == '' or 'sd_sentences' not in state:
                for _dest_text in dest_text.split('#'):
                    if '[' in _dest_text:
                        match = re.search(r'\[(\d+),\s*(\d+)\]', _dest_text)
                        if match:
                            offset_b, offset_e = map(int, match.groups())
                            log_append = ""
                        else:
                            offset_b, offset_e = 0, 0
                            log_append = "(Bracket detected in dest_text but offset time matching failed)"
                        _dest_text = _dest_text[:_dest_text.find('[')]
                    else:
                        log_append = ""
                        offset_b, offset_e = 0, 0
                    _dest_text = pre_proc(_dest_text)
                    ts = proc(recog_res_raw, timestamp, _dest_text)
                    for _ts in ts: all_ts.append([_ts[0] + offset_b * 16, _ts[1] + offset_e * 16])
                    if len(ts) > 1 and match:
                        log_append += '(offsets detected but No.{} sub-sentence matched to {} periods in audio, \
                            offsets are applied to all periods)'
            else:
                for _dest_spk in dest_spk.split('#'):
                    ts = proc_spk(_dest_spk, state['sd_sentences'])
                    for _ts in ts: all_ts.append(_ts)
                log_append = ""
        else:
            all_ts = timestamp_list
        ts = all_ts
        # ts.sort()
        srt_index = 0
        clip_srt = ""
        if len(ts):
            start, end = ts[0]
            start = min(max(0, start + start_ost * 16), len(data))
            end = min(max(0, end + end_ost * 16), len(data))
            res_audio = data[start:end]
            start_end_info = "from {} to {}".format(start / 16000, end / 16000)
            srt_clip, _, srt_index = generate_srt_clip(sentences, start / 16000.0, end / 16000.0, begin_index=srt_index)
            clip_srt += srt_clip
            for _ts in ts[1:]:  # multiple sentence input or multiple output matched
                start, end = _ts
                start = min(max(0, start + start_ost * 16), len(data))
                end = min(max(0, end + end_ost * 16), len(data))
                start_end_info += ", from {} to {}".format(start, end)
                res_audio = np.concatenate([res_audio, data[start + start_ost * 16:end + end_ost * 16]], -1)
                srt_clip, _, srt_index = generate_srt_clip(sentences, start / 16000.0, end / 16000.0,
                                                           begin_index=srt_index - 1)
                clip_srt += srt_clip
        if len(ts):
            message = "{} periods found in the speech: ".format(len(ts)) + start_end_info + log_append
        else:
            message = "No period found in the speech, return raw speech. You may check the recognition result and try other destination text."
            res_audio = data
        return (sr, res_audio), message, clip_srt

    def video_recog(self, video_filename, sd_switch='no', hotwords="", output_dir=None):
        video = mpy.VideoFileClip(video_filename)
        # Extract the base name, add '_clip.mp4', and 'wav'
        if output_dir is not None:
            os.makedirs(output_dir, exist_ok=True)
            _, base_name = os.path.split(video_filename)
            base_name, _ = os.path.splitext(base_name)
            clip_video_file = base_name + '_clip.mp4'
            audio_file = base_name + '.wav'
            audio_file = os.path.join(output_dir, audio_file)
        else:
            base_name, _ = os.path.splitext(video_filename)
            clip_video_file = base_name + '_clip.mp4'
            audio_file = base_name + '.wav'

        if video.audio is None:
            logging.error("No audio information found.")
            sys.exit(1)

        video.audio.write_audiofile(audio_file)
        wav = librosa.load(audio_file, sr=16000)[0]
        # delete the audio file after processing
        if os.path.exists(audio_file):
            os.remove(audio_file)
        state = {
            'video_filename': video_filename,
            'clip_video_file': clip_video_file,
            'video': video,
        }
        # res_text, res_srt = self.recog((16000, wav), state)
        return self.recog((16000, wav), sd_switch, state, hotwords, output_dir)

    def video_clip(self,
                   dest_text,
                   start_ost,
                   end_ost,
                   state,
                   font_size=32,
                   font_color='white',
                   add_sub=False,
                   dest_spk=None,
                   output_dir=None,
                   timestamp_list=None):
        # get from state
        recog_res_raw = state['recog_res_raw']
        timestamp = state['timestamp']
        sentences = state['sentences']
        video = state['video']
        clip_video_file = state['clip_video_file']
        video_filename = state['video_filename']

        #加入ai生成 timestamp_list
        print("timestamp_list",timestamp_list)
        if timestamp_list is None:
            all_ts = []
            if dest_spk is None or dest_spk == '' or 'sd_sentences' not in state:
                for _dest_text in dest_text.split('###'):
                    if '[' in _dest_text:
                        match = re.search(r'\[(\d+),\s*(\d+)\]', _dest_text)
                        if match:
                            offset_b, offset_e = map(int, match.groups())
                            log_append = ""
                        else:
                            offset_b, offset_e = 0, 0
                            log_append = "(Bracket detected in dest_text but offset time matching failed)"
                        _dest_text = _dest_text[:_dest_text.find('[')]
                    else:
                        offset_b, offset_e = 0, 0
                        log_append = ""
                    # import pdb; pdb.set_trace()
                    _dest_text = pre_proc(_dest_text)
                    ts = proc(recog_res_raw, timestamp, _dest_text.lower())
                    for _ts in ts: all_ts.append([_ts[0] + offset_b * 16, _ts[1] + offset_e * 16])
                    if len(ts) > 1 and match:
                        log_append += '(offsets detected but No.{} sub-sentence matched to {} periods in audio, \
                            offsets are applied to all periods)'
            else:
                for _dest_spk in dest_spk.split('#'):
                    ts = proc_spk(_dest_spk, state['sd_sentences'])
                    for _ts in ts: all_ts.append(_ts)
        else:  # AI clip pass timestamp as input directly
            all_ts = [[int(i[0]) * 16.0, int(i[1]) * 16.0] for i in timestamp_list]

        srt_index = 0
        time_acc_ost = 0.0
        ts = all_ts
        # ts.sort()
        clip_srt = ""
        if len(ts):
            if self.lang == 'en' and isinstance(sentences, str):
                sentences = sentences.split()
            start, end = ts[0][0] / 16000, ts[0][1] / 16000
            srt_clip, subs, srt_index = generate_srt_clip(sentences, start, end, begin_index=srt_index,
                                                          time_acc_ost=time_acc_ost)
            start, end = start + start_ost / 1000.0, end + end_ost / 1000.0
            video_clip = video.subclip(start, end)
            start_end_info = "from {} to {}".format(start, end)
            clip_srt += srt_clip
            if add_sub:
                generator = lambda txt: TextClip(txt, font='./font/STHeitiMedium.ttc', fontsize=font_size,
                                                 color=font_color)
                subtitles = SubtitlesClip(subs, generator)
                video_clip = CompositeVideoClip([video_clip, subtitles.set_pos(('center', 'bottom'))])
            concate_clip = [video_clip]
            time_acc_ost += end + end_ost / 1000.0 - (start + start_ost / 1000.0)
            for _ts in ts[1:]:
                start, end = _ts[0] / 16000, _ts[1] / 16000
                srt_clip, subs, srt_index = generate_srt_clip(sentences, start, end, begin_index=srt_index - 1,
                                                              time_acc_ost=time_acc_ost)
                if not len(subs):
                    continue
                chi_subs = []
                sub_starts = subs[0][0][0]
                for sub in subs:
                    chi_subs.append(((sub[0][0] - sub_starts, sub[0][1] - sub_starts), sub[1]))
                start, end = start + start_ost / 1000.0, end + end_ost / 1000.0
                _video_clip = video.subclip(start, end)
                start_end_info += ", from {} to {}".format(str(start)[:5], str(end)[:5])
                clip_srt += srt_clip
                if add_sub:
                    generator = lambda txt: TextClip(txt, font='./font/STHeitiMedium.ttc', fontsize=font_size,
                                                     color=font_color)
                    subtitles = SubtitlesClip(chi_subs, generator)
                    _video_clip = CompositeVideoClip([_video_clip, subtitles.set_pos(('center', 'bottom'))])
                    # _video_clip.write_videofile("debug.mp4", audio_codec="aac")
                concate_clip.append(copy.copy(_video_clip))
                time_acc_ost += end + end_ost / 1000.0 - (start + start_ost / 1000.0)
            message = "{} periods found in the audio: ".format(len(ts)) + start_end_info
            logging.warning("Concating...")
            if len(concate_clip) > 1:
                video_clip = concatenate_videoclips(concate_clip)
            # clip_video_file = clip_video_file[:-4] + '_no{}.mp4'.format(self.GLOBAL_COUNT)
            if output_dir is not None:
                os.makedirs(output_dir, exist_ok=True)
                _, file_with_extension = os.path.split(clip_video_file)
                clip_video_file_name, _ = os.path.splitext(file_with_extension)
                print(output_dir, clip_video_file)
                clip_video_file = os.path.join(output_dir,
                                               "{}_no{}.mp4".format(clip_video_file_name, self.GLOBAL_COUNT))
                temp_audio_file = os.path.join(output_dir,
                                               "{}_tempaudio_no{}.mp4".format(clip_video_file_name, self.GLOBAL_COUNT))
            else:
                clip_video_file = clip_video_file[:-4] + '_no{}.mp4'.format(self.GLOBAL_COUNT)
                temp_audio_file = clip_video_file[:-4] + '_tempaudio_no{}.mp4'.format(self.GLOBAL_COUNT)
            video_clip.write_videofile(clip_video_file, audio_codec="aac", temp_audiofile=temp_audio_file)
            self.GLOBAL_COUNT += 1
        else:
            clip_video_file = video_filename
            message = "No period found in the audio, return raw speech. You may check the recognition result and try other destination text."
            srt_clip = ''
        return clip_video_file, message, clip_srt


funasr_model_zh = AutoModel(model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                vad_model="damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
                punc_model="damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
                spk_model="damo/speech_campplus_sv_zh-cn_16k-common",
                )
audio_clipper = VideoClipper(funasr_model_zh)
audio_clipper.lang = 'zh'