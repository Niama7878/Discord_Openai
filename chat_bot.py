from seleniumwire import webdriver  
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os

# 读取环境变量
load_dotenv()
DISCORD_ACCOUNT_TOKEN = os.getenv("DISCORD_ACCOUNT_TOKEN")

# Discord 频道 URL
DISCORD_CHANNEL_URL = ""

# 启动 WebDriver
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
prefs = {
    "profile.default_content_setting_values.media_stream_mic": 1  # 自动允许网站使用麦克风
}
chrome_options.add_experimental_option("prefs", prefs)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

def login_with_token():
    """用 Token 直接登录 Discord"""
    try:
        driver.get("https://discord.com/login")

        # 在 DevTools 里注入 Token
        script = f"""
        function login(token) {{
            setInterval(() => {{
                document.body.appendChild(document.createElement `iframe`).contentWindow.localStorage.token = `"${{token}}"`;
            }}, 50);
            setTimeout(() => {{
                location.reload();
            }}, 1000);
        }}
        login("{DISCORD_ACCOUNT_TOKEN}");
        """
        driver.execute_script(script)  # 执行 JavaScript
        driver.get(DISCORD_CHANNEL_URL)
        
    except Exception as e:
        print(f"登录失败，错误信息: {e}")

def join_voice_channel(xpath: str):
    """加入 Discord 语音频道"""
    try:
        join_button = driver.find_element(By.XPATH, xpath)
        join_button.click()
    except Exception as e:
        print(f"无法加入语音频道: {e}")

def leave_voice_channel():
    """离开 Discord 语音频道"""
    try:
        leave_button = driver.find_element(By.XPATH, '//*[@id="app-mount"]/div[2]/div[1]/div[1]/div/div[2]/div/div/div/div/div[1]/section/div[1]/div/div[1]/div[2]/button[2]')
        leave_button.click()
    except Exception as e:
        print(f"无法离开语音频道: {e}")

login_with_token()