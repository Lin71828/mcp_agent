from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from loguru import logger
import requests
from bs4 import BeautifulSoup

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
    """查找和输入内容相关的信息, query越简单概括越好, 网站信息需要进一步调用search_url()函数进行查看

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

@mcp.tool()
async def search_url(url: str, query: str) -> str:
    """对给定url对应的网站的信息进行读取
    
    参数:
        url: 要搜索的网址
        
    返回:
        str: 包含HTML提取内容
    """
    try:
        # 第一部分：获取并分析HTML内容
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # 异步获取HTML内容
        async with httpx.AsyncClient() as client:
            html_response = await client.get(url, headers=headers, timeout=10.0)
            html_response.raise_for_status()
            
        soup = BeautifulSoup(html_response.text, 'html.parser')
        
        # 移除不需要的标签
        for element in soup(['script', 'style', 'noscript', 'meta', 'link']):
            element.decompose()
        
        # 提取主要文本内容
        text_content = soup.get_text('\n', strip=True)
        text_content = '\n'.join([line for line in text_content.split('\n') if line.strip()])
        
        # 提取重要结构化数据
        structured_data = {
            'title': soup.title.string if soup.title else '无标题',
            'headings': {
                'h1': [h1.get_text(strip=True) for h1 in soup.find_all('h1')],
                'h2': [h2.get_text(strip=True) for h2 in soup.find_all('h2')],
                'h3': [h3.get_text(strip=True) for h3 in soup.find_all('h3')],
            },
            'links': [{'text': a.get_text(strip=True), 'href': a.get('href')} 
                     for a in soup.find_all('a') if a.get('href')],
            'images': [img.get('src') for img in soup.find_all('img') if img.get('src')]
        }
        
        html_analysis = (
            f"HTML文本内容摘要:\n{text_content[:2000]}...\n\n"
            # f"结构化数据:\n{json.dumps(structured_data, indent=2, ensure_ascii=False)}"
        )
        
        # 组合两部分结果
        return (
            f"网页分析结果:\n\n"
            f"=== HTML内容 ===\n{html_analysis}\n\n"
        )
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP请求失败: {e}")
        return f"无法访问URL: {str(e)}"
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return f"搜索时出现错误: {str(e)}"


if __name__ == "__main__":
    # 初始化并运行服务器
    mcp.run(transport='stdio')