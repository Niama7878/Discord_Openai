# Discord Openai

一个基于 Discord Bot 和 OpenAI API 的多模态实时语音、文本和图像交互系统

## 项目简介

本项目旨在构建一个集实时语音对话、文本问答、图像生成/编辑以及语音合成与转写于一体的系统。借助 Discord Bot、OpenAI API 及其他技术如 Selenium 自动登录 Discord 频道、PyAudio 音频捕获与播放。

主要功能包括：

- **实时语音对话**：捕获音频数据，通过 WebSocket 与 OpenAI 实时通信，实现语音转写和语音回复。
- **文本问答**：利用 GPT-4o 模型，支持用户输入文本及图像输入进行对话。
- **图像生成与编辑**：整合 DALL·E 3 和 DALL·E 2 提供图片生成和编辑功能。
- **语音合成与转写**：通过 OpenAI TTS 与 Whisper 模型，实现语音生成和语音转文字。

## 安装依赖

请确保已安装 Python（此项目开发使用 Python 3.12.8 ），然后运行以下命令安装项目依赖：

```bash
pip install openai discord.py python-dotenv PyAudio websocket-client pydub selenium-wire blinker==1.4 webdriver-manager
```

## 环境变量配置

请在项目根目录下找到 `.env` 文件，并配置如下变量：

```dotenv
OPENAI_API_KEY=your_openai_api_key
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_ACCOUNT_TOKEN=your_discord_account_token
```

确保这些变量的值均为有效的凭证，否则可能导致 API 调用或 Discord 登录失败。

## 项目结构

项目主要包含以下几个模块：

- **chat.py**  
  负责实时语音处理与 WebSocket 通信，采集音频并将音频数据发送到 OpenAI 服务器，同时处理服务器返回的语音文本和音频增量数据。

- **chat_bot.py**  
  通过 Selenium 实现 Discord 自动登录，并提供加入和离开语音频道的功能。

- **main.py**  
  项目的入口，利用 Discord Bot 框架注册各类命令（如文本问答、图片生成、语音生成、实时语音对话等），并处理用户交互。

- **play.py**  
  提供音频播放支持，利用 PyAudio 在后台播放从服务器返回的音频数据。

- **status.py**  
  用于管理全局处理状态，确保实时对话过程中状态同步正确。

- **test.py**  
  用于检测系统所需的音频设备，帮助开发者调试设备配置。

## 使用说明

1. **启动 Discord Bot**  
   配置好环境变量后，运行 `main.py` 启动 Discord Bot。Bot 启动后会自动同步命令树，你可以通过 Discord 指令来调用各项功能：

   - `/ask_gpt`：与 GPT-4o 进行文本问答，支持图像输入。
   - `/generate_speech`：生成语音文件。
   - `/transcribe_audio`：将语音转写为文字。
   - `/generate_image`：生成图片（DALL·E 3）。
   - `/edit_image`：编辑图片（DALL·E 2）。
   - `/realtime_chat`：启动实时语音对话功能（请确保已加入语音频道）。

2. **实时语音对话**  
   通过 `/realtime_chat` 命令，Bot 会利用 Selenium 自动登录 Discord 并加入指定语音频道，此时系统会开始捕获麦克风音频，进行实时交互。

3. **其他功能**  
   根据需要使用其他命令，实现图像生成、语音生成及转写等功能，具体的参数和使用方法可参考各命令描述。

## 注意事项

- **并发控制**  
  部分 API 调用使用了异步编程和并发控制（例如 `asyncio.Semaphore`）来防止速率超标，请根据实际使用场景进行调整。

- **设备配置**  
  通过 `test.py` 检测所需的音频设备，确保在使用实时语音功能时麦克风与播放设备配置正确。

## 使用教程

[YouTube](https://youtu.be/JiZUEQmwS1E) [Bilibili](https://www.bilibili.com/video/BV1R3odYwEEr)