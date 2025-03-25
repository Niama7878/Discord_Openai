import discord
from discord.ext import commands
import openai
import os
import asyncio
from discord import app_commands
from dotenv import load_dotenv
from pathlib import Path
from uuid import uuid4
import json
import base64
import mimetypes
from chat_bot import join_voice_channel, leave_voice_channel
from chat import response_create

load_dotenv() # 加载 .env 文件中的环境变量
openai.api_key = os.getenv("OPENAI_API_KEY")  # 读取 OpenAI API Key
token = os.getenv("DISCORD_BOT_TOKEN")  # 读取 Discord Bot Token

client = openai.OpenAI()  # 初始化 OpenAI 客户端

intents = discord.Intents.all()  # 启用所有意图
bot = commands.Bot(command_prefix="/", intents=intents)  # 创建 Bot 实例
tree = bot.tree  # 获取命令树

# 定义选项列表
size_choices_dalle3 = [
    app_commands.Choice(name="1024x1024", value="1024x1024"),
    app_commands.Choice(name="1792x1024", value="1792x1024"),
    app_commands.Choice(name="1024x1792", value="1024x1792")
]

style_choices = [
    app_commands.Choice(name="Vivid", value="vivid"),
    app_commands.Choice(name="Natural", value="natural")
]

size_choices_dalle2 = [
    app_commands.Choice(name="256x256", value="256x256"),
    app_commands.Choice(name="512x512", value="512x512"),
    app_commands.Choice(name="1024x1024", value="1024x1024")
]

speech_choices = [
    app_commands.Choice(name="MP3", value="mp3"),
    app_commands.Choice(name="WAV", value="wav")
]

voice_choices = [
    app_commands.Choice(name="Alloy", value="alloy"),
    app_commands.Choice(name="Ash", value="ash"),
    app_commands.Choice(name="Ballad", value="ballad"),
    app_commands.Choice(name="Coral", value="coral"),
    app_commands.Choice(name="Echo", value="echo"),
    app_commands.Choice(name="Fable", value="fable"),
    app_commands.Choice(name="Onyx", value="onyx"),
    app_commands.Choice(name="Nova", value="nova"),
    app_commands.Choice(name="Sage", value="sage"),
    app_commands.Choice(name="Shimmer", value="shimmer"),
    app_commands.Choice(name="Verse", value="verse")
]

response_choice = [
    app_commands.Choice(name="Text", value="text"),
    app_commands.Choice(name="JSON", value="json"),
    app_commands.Choice(name="SRT", value="srt"),
    app_commands.Choice(name="Verbose JSON", value="verbose_json"),
    app_commands.Choice(name="VTT", value="vtt")
]

active_sessions = {} # 记录当前正在使用实时对话功能的用户

xpaths = {
    "常规": "//*[@id='channels']/ul/li[5]/div/div/div/a/div[1]/div[2]",
    "new": "//*[@id='channels']/ul/li[6]/div/div/div/a/div[1]/div[2]",
}

api_semaphore = asyncio.Semaphore(4)  # 限制 OpenAI API 并发调用，防止速率超标

def image_to_base64(image_path):
    # 将图片文件转换为 base64 编码
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

@tree.command(name="ask_gpt", description="使用 GPT-4o 进行问答，可选图像输入")
async def ask_gpt(interaction: discord.Interaction, prompt: str, image_url: str = None, image_file: discord.Attachment = None, temperature: float = 1.0):
    await interaction.response.defer()  # 延迟响应，防止超时
    
    if temperature < 0 or temperature > 2:
        await interaction.followup.send("温度参数必须在 0 到 2 之间！", ephemeral=True)
        return
    
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    
    if image_url:
        messages[0]["content"].append({"type": "image_url", "image_url": {"url": image_url}})
    
    if image_file:
        ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}  # 允许的图片格式
        file_extension = Path(image_file.filename).suffix.lower()  # 获取文件扩展名（小写）

        if file_extension not in ALLOWED_EXTENSIONS:  # 检查是否为允许的图片格式
            await interaction.followup.send(f"不支持的图片格式: `{file_extension}`\n请上传以下格式的图片: {', '.join(ALLOWED_EXTENSIONS)}")
            return
        
        image_path = Path(f"temp_{uuid4().hex}{file_extension}")
        await image_file.save(image_path)
        base64_image = image_to_base64(image_path)

        mime_type, _ = mimetypes.guess_type(image_file.filename)  
        if not mime_type:
            mime_type = "application/octet-stream"  

        messages[0]["content"].append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}})
    
    try:
        async with asyncio.Semaphore(3):
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o",
                messages=messages,
                temperature=temperature
            )

        result = response.choices[0].message.content 
        
        await interaction.followup.send(f"GPT-4o 回复:\n```{result}```")
    except Exception as e:
        await interaction.followup.send(f"生成回复出错: {e}")
    finally:
        if image_path:
            await asyncio.to_thread(image_path.unlink)

@tree.command(name="generate_speech", description="使用 OpenAI 生成语音")
@app_commands.choices(format=speech_choices, voice=voice_choices)
async def generate_speech(interaction: discord.Interaction, text: str, format: str, voice: str, speed: float = 1.0):
    await interaction.response.defer()  # 延迟响应，防止超时
    
    if speed < 0.25 or speed > 4.0:
        await interaction.followup.send("语速必须在 0.25 到 4.0 之间！", ephemeral=True)
        return
    
    speech_file_path = Path(f"speech_{uuid4().hex}.{format}")
    
    try:
        async with api_semaphore:  # 限制并发请求，防止 API 超载
            response = await asyncio.to_thread(
                openai.audio.speech.create,
                model="tts-1-hd",
                voice=voice,
                input=text,
                response_format=format,
                speed=speed
            )
        
        audio_data = response.content  # 直接提取内容
        
        with speech_file_path.open("wb") as f:  # 直接写入文件
            f.write(audio_data)

        await interaction.followup.send(
            file=discord.File(speech_file_path, filename=speech_file_path.name)
        )
    except Exception as e:
        await interaction.followup.send(f"生成语音时出错: {e}")
    finally:
        await asyncio.to_thread(speech_file_path.unlink)

@tree.command(name="transcribe_audio", description="使用 OpenAI Whisper 进行语音转文字")
@app_commands.choices(response_format=response_choice)
async def transcribe_audio(interaction: discord.Interaction, audio: discord.Attachment, response_format: str):
    await interaction.response.defer()  # 延迟响应，防止超时

    ALLOWED_EXTENSIONS = {".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".wav", ".webm"}  # 允许的音频格式
    file_extension = Path(audio.filename).suffix.lower()  # 获取文件扩展名（转小写）
    
    if file_extension not in ALLOWED_EXTENSIONS:  # 如果文件扩展名不在允许的范围内，拒绝处理
        await interaction.followup.send(f"不支持的音频格式: `{file_extension}`\n请上传以下格式的文件: {', '.join(ALLOWED_EXTENSIONS)}")
        return
    
    audio_path = Path(f"temp_{uuid4().hex}{Path(audio.filename).suffix}")  # 生成临时文件路径
    transcript_file_path = None  
    
    try:
        await audio.save(audio_path)  # 下载文件到本地
        
        async with api_semaphore:  # 限制 API 并发请求
            with audio_path.open("rb") as f:
                response = await asyncio.to_thread(
                    client.audio.transcriptions.create,
                    model="whisper-1",
                    file=f,  
                    response_format=response_format
                )
        
        if response_format == "text":
            await interaction.followup.send(f"转录结果 ({response_format}): \n```{response}```")
        else:
            if response_format in ["json", "verbose_json"]:
                file_ext = "json"  # 统一为 .json 文件
            else:
                file_ext = response_format  # 其他格式保持不变

            transcript_file_path = Path(f"transcript_{uuid4().hex}.{file_ext}")

            with transcript_file_path.open("w", encoding="utf-8") as f:
                if hasattr(response, "model_dump"):  # 适用于 Pydantic 模型
                    json.dump(response.model_dump(), f, ensure_ascii=False, indent=4)
                else:
                    f.write(response)  

            await interaction.followup.send(
                f"转录结果 ({response_format}) 已生成:",
                file=discord.File(transcript_file_path, filename=transcript_file_path.name)
            )
    
    except Exception as e:
        await interaction.followup.send(f"语音转文字失败: {e}")
    
    finally:
        await asyncio.to_thread(audio_path.unlink)  
        if transcript_file_path:
            await asyncio.to_thread(transcript_file_path.unlink)  

@tree.command(name="generate_image", description="使用 DALL·E 3 生成图片")
@app_commands.choices(size=size_choices_dalle3, style=style_choices)
async def generate_image(interaction: discord.Interaction, prompt: str, size: str, style: str):
    await interaction.response.defer()  # 先延迟响应，防止超时
    
    try:
        async with api_semaphore:  # 限制并发请求
            response = await asyncio.to_thread(
                client.images.generate,
                model="dall-e-3",
                prompt=prompt,
                n=1,
                quality="hd",
                size=size,
                style=style
            )

        image_url = response.data[0].url
        await interaction.followup.send(f"生成的图片: {image_url}")  
    except Exception as e:
        await interaction.followup.send(f"生成图片时出错: {e}")  

@tree.command(name="edit_image", description="使用 DALL·E 2 编辑图片")
@app_commands.choices(size=size_choices_dalle2)
async def edit_image(interaction: discord.Interaction, image: discord.Attachment, mask: discord.Attachment, prompt: str, size: str, n: int = 1):
    await interaction.response.defer()  # 延迟响应，防止超时

    ALLOWED_EXTENSIONS = {".png"}  # 允许的图片格式

    # 获取文件扩展名（转小写）
    image_ext = Path(image.filename).suffix.lower()
    mask_ext = Path(mask.filename).suffix.lower()

    if image_ext not in ALLOWED_EXTENSIONS:  # 检查 image 格式
        await interaction.followup.send(f"不支持的图片格式: `{image_ext}`\n请上传 PNG 格式的图片。")
        return

    if mask_ext not in ALLOWED_EXTENSIONS:  # 检查 mask 格式
        await interaction.followup.send(f"不支持的遮罩图片格式: `{mask_ext}`\n请上传 PNG 格式的遮罩图片。")
        return
    
    if n < 1 or n > 10:
        await interaction.followup.send("图片数量必须在 1 到 10 之间！", ephemeral=True)
        return
    
    image_path = Path(f"temp_{uuid4().hex}.png")
    mask_path = Path(f"temp_mask_{uuid4().hex}.png")

    # 让文件 I/O 在后台线程中执行，避免阻塞
    await asyncio.to_thread(image.save, image_path)
    await asyncio.to_thread(mask.save, mask_path)

    try:
        async with api_semaphore:  # 限制并发请求
            async with image_path.open("rb") as img, mask_path.open("rb") as msk:
                response = await asyncio.to_thread(
                    client.images.edit,
                    image=img,
                    mask=msk,
                    prompt=prompt,
                    n=n,
                    size=size
                )

        image_urls = "\n".join([item.url for item in response.data])
        await interaction.followup.send(f"编辑后的图片:\n{image_urls}")
    except Exception as e:
        await interaction.followup.send(f"编辑图片时出错: {e}")
    finally:
        await asyncio.to_thread(image_path.unlink)  
        await asyncio.to_thread(mask_path.unlink)  

@bot.tree.command(name="realtime_chat", description="使用 GPT-4o 实时对话")
@app_commands.choices(voice=voice_choices)
async def realtime_chat(interaction: discord.Interaction, voice: str):
    # 全局锁定：如果已有用户正在会话，则拒绝所有其他用户调用
    if active_sessions:
        await interaction.response.send_message("目前已有用户正在使用实时对话功能，请等待当前用户退出语音频道后再使用！", ephemeral=True)
        return

    # 检查用户是否在语音频道中
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("请先加入一个语音频道！", ephemeral=True)
        return

    voice_channel = interaction.user.voice.channel
    channel_name = voice_channel.name
    xpath = xpaths.get(channel_name, xpaths["常规"])

    try:
        await interaction.response.defer(ephemeral=True)  # 延迟响应防止超时

        join_voice_channel(xpath) # 加入语音频道
        active_sessions[interaction.user.id] = voice_channel.id # 全局锁定：记录该用户的语音频道 ID
        response_create["response"]["voice"] = voice # 设置语音模型

        await interaction.followup.send(f"已成功加入语音频道 `{channel_name}`。现在您可以开始实时对话体验了！", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"加入语音频道失败: {e}", ephemeral=True)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    # 只处理在 active_sessions 中的用户（全局只有一个）
    if member.id in active_sessions:
        if not after.channel or after.channel.id != active_sessions[member.id]: # 如果用户离开了语音频道，或更换了频道
            leave_voice_channel()
            active_sessions.clear()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # 避免机器人回复自己

@bot.event
async def on_ready():
    await tree.sync()  # 同步命令树
    print(f"{bot.user} 启动成功！")  

async def main():
    async with bot:
        await bot.start(token)  # 启动 Bot

asyncio.run(main())  # 运行主函数