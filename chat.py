import os
from dotenv import load_dotenv
import json
import base64
import threading
import pyaudio
from play import AudioPlayer
from status import processing
import websocket
import io
from pydub import AudioSegment

# 读取环境变量
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# WebSocket 配置
OPENAI_WS_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17"
HEADERS = [
    "Authorization: Bearer " + OPENAI_API_KEY,
    "OpenAI-Beta: realtime=v1"
]
ws_global = None # 全局 WebSocket 连接

FORMAT = pyaudio.paInt16  # 16位 PCM
CHANNELS = 2  # 声道
RATE = 16000  # 采样率 
CHUNK = 1024  # 每次读取的帧数

response_create = {
    "type": "response.create",
    "response": {
        "modalities": ["audio", "text"],
        "instructions": "根据上下文推理生成精简回复",
        "voice": "",
        "temperature": 1.0,
        "input": [],  # 存放聊天记录
    }
}

player = AudioPlayer()

def on_message(ws, message):
    """处理 WebSocket 收到的消息"""
    data = json.loads(message)  # 解析收到的消息
    event_type = data.get("type") # 获取消息类型
   
    if event_type == "input_audio_buffer.speech_started":
        print("检测到语音开始！")

    elif event_type == "input_audio_buffer.speech_stopped":
        print("检测到语音停止！")

    elif event_type in ["conversation.item.input_audio_transcription.completed", "response.audio_transcript.done"]:
        content = data.get("transcript", "") 
        
        if content and content.strip():
            construct_message(event_type, content)
            processing(True) # 开启处理状态

    elif event_type == "response.audio.delta":
        audio_data = base64.b64decode(data.get("delta", ""))
        # 使用 pydub 解析 bytes 数据
        audio = AudioSegment.from_raw(io.BytesIO(audio_data), sample_width=2, frame_rate=11025, channels=2)
        
        # 直接保存为 WAV 格式
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        audio_bytes = wav_io.getvalue()

        player.add_audio(audio_bytes) # 传入 WAV bytes 数据

    elif event_type == "response.done":
        processing(False) # 取消处理状态
        response_create["response"]["input"].clear() # 清空聊天记录
        ws_global.close() # 关闭 WebSocket 连接
        
def on_open(ws):
    """当 WebSocket 打开时，发送 session.update 消息"""
    try:
        session_update = {
            "type": "session.update",
            "session": {
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "create_response": False
                }
            }
        }
        ws_global.send(json.dumps(session_update))
        
    except Exception as e:
        print(f"on_open 过程中发生错误: {e}")

def connect_ws():
    """建立 WebSocket 连接""" 
    global ws_global

    try:
        ws_global = websocket.WebSocketApp(
            OPENAI_WS_URL,
            header=HEADERS,
            on_open=on_open,
            on_message=on_message,
            on_close=on_close,
            on_error=on_error,
        )
        threading.Thread(target=ws_global.run_forever, daemon=True).start()

    except Exception as e:
        print(f"OpenAI WebSocket 连接失败：{e}")

def on_close(ws, close_status_code, close_msg):
    """WebSocket 断开时触发"""
    #print(f"OpenAI WebSocket 关闭信息：{close_status_code}, {close_msg}")
    connect_ws() # 尝试重新连接

def on_error(ws, error):
    """WebSocket 发送错误时触发"""
    print(f"OpenAI WebSocket 错误：{error}")

def send_audio_data(pcm16_audio):
    """发送 Base64 编码的音频数据到 WebSocket 服务器"""
    try:
        base64_audio = base64.b64encode(pcm16_audio).decode()
        event = {
            "type": "input_audio_buffer.append",
            "audio": base64_audio
        }
        if ws_global:
            ws_global.send(json.dumps(event))

    except Exception as e:
        pass

def audio_stream():
    """监听输出设备的音频并发送到 WebSocket"""
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, input_device_index=25, frames_per_buffer=CHUNK)
    
    while True:
        if not processing() and not player.is_playing:
            pcm_data = stream.read(CHUNK, exception_on_overflow=False)
            send_audio_data(pcm_data)

def construct_message(event_type, content):
    """构造聊天信息并发送到 WebSocket"""
    role = ("user" if event_type == "conversation.item.input_audio_transcription.completed" else "assistant")

    message = {
        "type": "message",
        "role": role,
        "content": [{"type": "input_text" if role == "user" else "text", "text": content}]
    }

    response_create["response"]["input"].append(message)
    print(f"{role}: {content}")

    # 仅在 user 说话时触发 dc.send
    if event_type == "conversation.item.input_audio_transcription.completed":
        ws_global.send(json.dumps(response_create)) 

connect_ws()
threading.Thread(target=audio_stream, daemon=True).start()