from typing import Any
# import httpx
from mcp.server.fastmcp import FastMCP
from loguru import logger
# from duckduckgo_search import DDGS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from openai import OpenAI
import base64
import os
import io
from dotenv import load_dotenv
from PIL import Image
import requests
from bs4 import BeautifulSoup
import time
import shutil


# 初始化 FastMCP 服务器
mcp = FastMCP("tools")
logger.debug("FastMCP 服务器启动中...")

@mcp.tool()
async def save_to_file(content,output_path) -> str:
    """将输出内容保存到指定文件中。

    参数:
        content: 要保存的内容
        output_path: 要保存到的路径
    """
    try:
        with open(output_path, 'w') as f:
            f.write(content)
        return f"内容已保存到文件 '{output_path}'"
    except Exception as e:
        return f"保存文件时出现错误: {e}"

@mcp.tool()
async def search_engine(query:str, ) -> str:
    """查找和输入内容相关的url, 网站信息需要进一步调用search_url()函数进行查看

    参数:
        query: 要搜索的内容
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    num_results=5
    try:
        url = f"https://www.bing.com/search?q={query}&count={num_results}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Bing的搜索结果选择器（可能会随Bing更新而变化）
        results = soup.find_all('li', class_='b_algo')
        
        search_results = []  # 存储结果的列表
        
        for i, result in enumerate(results, 1):
            title = result.find('h2').text
            link = result.find('a')['href']
            search_results.append({
                "index": i,
                "title": title,
                "url": link
            })
            
        return search_results  # 返回结构化数据
        
    except Exception as e:
        print(f"Bing搜索出错: {e}")
        return []  # 出错时返回空列表

def full_page_screenshot(url, output_path='full_page.png'):
    # 设置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式
    chrome_options.add_argument('--start-maximized')
    
    # 初始化浏览器
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get(url)
        
        # 获取页面的总高度
        total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
        
        # 设置窗口大小为页面总高度
        driver.set_window_size(1920, total_height)
        
        # 等待页面加载（根据需要调整）
        driver.implicitly_wait(10)
        
        # 保存截图
        driver.save_screenshot(output_path)
        # print(f"完整页面截图已保存到: {output_path}")
    finally:
        driver.quit()

def analyze_image_with_qwen(image_path, prompt="描述图片内容."):
    """
    使用Qwen2-VL模型分析图片并返回描述
    
    参数:
        image_path (str): 要分析的图片路径
        prompt (str): 对图片的提示问题，默认为"描述图片内容"
        
    返回:
        str: 模型生成的图片描述
    """
    def convert_image_to_webp_base64(input_image_path):
        try:
            with Image.open(input_image_path) as img:
                byte_arr = io.BytesIO()
                img.save(byte_arr, format='webp')
                byte_arr = byte_arr.getvalue()
                base64_str = base64.b64encode(byte_arr).decode('utf-8')
                return base64_str
        except IOError:
            print(f"Error: Unable to open or convert the image {input_image_path}")
            return None

    # 加载环境变量
    load_dotenv()

    # 初始化OpenAI客户端
    client = OpenAI(
        api_key=os.environ['API_KEY'], # 从https://cloud.siliconflow.cn/account/ak获取
        base_url="https://api.siliconflow.cn/v1"
    )

    # 获取图片的base64编码
    image_base64 = convert_image_to_webp_base64(image_path)
    if not image_base64:
        return None

    # 调用API
    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-VL-32B-Instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                        }
                    },
                    {
                        "type": "text",
                        "text": "无视无关问题的图片信息, 根据图片内容回答:" + prompt
                    }
                ]
            }
        ],
        stream=True
    )

    # 收集响应
    result = ""
    for chunk in response:
        chunk_message = chunk.choices[0].delta.content
        if chunk_message:  # 确保chunk_message不是None
            result += chunk_message

    return result

@mcp.tool()
async def search_url(url:str,query:str) -> str:
    """对给定url对应的网站的信息进行读取

    参数:
        url: 要识别的网站
        query:要在网站上读取的信息(自然语言描述)
    """
    try:
        path=f'./tmp/{time.strftime("%Y%m%d_%H%M%S")}.png'
        full_page_screenshot(url,output_path=path)
        results=analyze_image_with_qwen(path,query)
        print(url,":",results)
        return f"搜索结果 '{results}'"
    except Exception as e:
        print("url:error")
        return f"搜索时出现错误: {e}"

if __name__ == "__main__":
    # 初始化并运行服务器
    mcp.run(transport='stdio')