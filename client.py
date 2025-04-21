import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Optional

import requests
from dotenv import load_dotenv
from loguru import logger

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 加载环境变量
load_dotenv()

# 配置常量
MAX_TOOL_CALLS = 5  # 每轮对话最大工具调用次数
logger.debug("FastMCP 客户端启动中...")


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.stdio = None
        self.write = None
        
        # API 配置
        self.api_config = {
            "api_key": os.environ["DS_API_KEY"],
            "base_url": os.environ["DS_API_BASE"],
            "model": os.environ["API_MODEL_NAME"],
            "headers": {
                "Authorization": f"Bearer {os.environ['DS_API_KEY']}",
                "Content-Type": "application/json"
            }
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def connect(self, server_script: str):
        """连接到 MCP 服务器"""
        if not server_script.endswith((".py", ".js")):
            raise ValueError("服务器脚本必须是 .py 或 .js 文件")

        command = "python" if server_script.endswith(".py") else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script], env=None
        )

        # 建立连接
        self.stdio, self.write = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()
        await self._log_available_tools()

    async def _log_available_tools(self):
        """记录可用工具信息"""
        response = await self.session.list_tools()
        tools_info = [
            [tool.name, tool.description, tool.inputSchema] 
            for tool in response.tools
        ]
        logger.info(f"可用工具: {tools_info}")

    def _call_api(self, messages: list, tools: list = None) -> dict:
        """调用对话API"""
        payload = {
            "model": self.api_config["model"],
            "messages": messages,
            "max_tokens": 1000
        }
        
        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(
                f"{self.api_config['base_url']}/chat/completions",
                headers=self.api_config["headers"],
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API调用失败: {e}")
            raise

    async def _process_tool_calls(self, tool_calls: list, messages: list) -> None:
        """处理工具调用并将结果加入消息历史"""
        for call in tool_calls:
            try:
                tool_name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])
                
                logger.debug(f"调用工具: {tool_name}，参数: {args}")
                result = await self.session.call_tool(tool_name, args)
                
                # 确保结果为字符串
                if isinstance(result, bytes):
                    result = result.decode('utf-8', errors='replace')
                result = str(result)
                
                messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": call["id"]
                })
                
            except Exception as e:
                logger.error(f"工具调用失败: {e}")
                messages.append({
                    "role": "tool",
                    "content": f"Error: {str(e)}",
                    "tool_call_id": call["id"]
                })

    async def query(self, user_input: str) -> str:
        """处理用户查询并返回响应"""
        messages = [{"role": "user", "content": user_input}]
        tool_calls_count = 0
        
        while True:
            # 获取可用工具
            tools_response = await self.session.list_tools()
            available_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": getattr(tool, "inputSchema", {}),
                    },
                }
                for tool in tools_response.tools
            ] if tool_calls_count < MAX_TOOL_CALLS else None

            # 获取模型响应
            response = self._call_api(messages, available_tools)
            message = response["choices"][0]["message"]
            
            # 添加助手消息到历史
            msg = {"role": "assistant", "content": message.get("content", "")}
            if "tool_calls" in message:
                msg["tool_calls"] = message["tool_calls"]
            messages.append(msg)

            # 检查是否需要工具调用
            if not message.get("tool_calls") or tool_calls_count >= MAX_TOOL_CALLS:
                return message.get("content", "")

            # 处理工具调用
            await self._process_tool_calls(message["tool_calls"], messages)
            tool_calls_count += 1

    async def interactive_chat(self):
        """交互式聊天界面"""
        print("\nMCP 客户端已就绪！输入问题或 'quit' 退出")
        
        while True:
            try:
                user_input = input("\nQuery: ").strip()
                if user_input.lower() == "quit":
                    break
                    
                response = await self.query(user_input)
                print(f"\n{response}")
                
            except Exception as e:
                logger.error(f"处理查询时出错: {e}")
                print(f"\n错误: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("用法: python client.py <服务器脚本路径>")
        return

    async with MCPClient() as client:
        await client.connect(sys.argv[1])
        await client.interactive_chat()


if __name__ == "__main__":
    asyncio.run(main())