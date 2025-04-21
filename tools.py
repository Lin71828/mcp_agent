from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from loguru import logger

# 初始化 FastMCP 服务器
mcp = FastMCP("tools")
logger.debug("FastMCP 服务器启动中...")

@mcp.tool()
async def save_to_file(content) -> str:
    """将输出内容保存到文件中。

    参数:
        content: 要保存的内容
    """
    try:
        with open('output.txt', 'w') as f:
            f.write(content)
        return f"内容已保存到文件 '{'output.txt'}'"
    except Exception as e:
        return f"保存文件时出现错误: {e}"

if __name__ == "__main__":
    # 初始化并运行服务器
    mcp.run(transport='stdio')