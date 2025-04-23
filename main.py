import sys
import os
import asyncio
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
from typing import Optional
import logging
from client import MCPClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 最大工具调用次数
MAX_TOOL_CALLS = 5

# 默认服务器路径
DEFAULT_SERVER_PATH = "./tools.py"

class MCPClientGUI:
    def __init__(self, root):
        self.root = root
        self.client: Optional[MCPClient] = None
        self.loop = asyncio.get_event_loop()
        self.running = False
        
        self.setup_ui()
        
        # 检查并设置默认服务器路径
        self.set_default_server_path()
        
    def set_default_server_path(self):
        """设置默认服务器路径"""
        if os.path.exists(DEFAULT_SERVER_PATH):
            self.server_path_entry.delete(0, tk.END)
            self.server_path_entry.insert(0, DEFAULT_SERVER_PATH)
            self.append_message("系统", f"检测到默认服务器脚本: {DEFAULT_SERVER_PATH}")
        else:
            self.append_message("系统", f"未找到默认服务器脚本: {DEFAULT_SERVER_PATH}")

    def setup_ui(self):
        """设置用户界面"""
        self.root.title("MCP 客户端")
        self.root.geometry("1000x700")
        
        # 顶部连接面板
        self.connection_frame = tk.Frame(self.root)
        self.connection_frame.pack(pady=10, fill=tk.X)
        
        self.server_path_label = tk.Label(self.connection_frame, text="服务器脚本路径:")
        self.server_path_label.pack(side=tk.LEFT, padx=5)
        
        self.server_path_entry = tk.Entry(self.connection_frame, width=50)
        self.server_path_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.browse_button = tk.Button(self.connection_frame, text="浏览...", command=self.browse_server_script)
        self.browse_button.pack(side=tk.LEFT, padx=5)
        
        self.connect_button = tk.Button(self.connection_frame, text="连接", command=self.toggle_connection)
        self.connect_button.pack(side=tk.LEFT, padx=5)
        
        # API配置面板
        self.api_frame = tk.Frame(self.root)
        self.api_frame.pack(pady=5, fill=tk.X)
        
        tk.Label(self.api_frame, text="API配置:").pack(side=tk.LEFT, padx=5)
        
        self.api_key_entry = tk.Entry(self.api_frame, width=30, show="*")
        self.api_key_entry.pack(side=tk.LEFT, padx=5)
        self.api_key_entry.insert(0, os.getenv("DS_API_KEY", ""))
        
        self.api_base_entry = tk.Entry(self.api_frame, width=40)
        self.api_base_entry.pack(side=tk.LEFT, padx=5)
        self.api_base_entry.insert(0, os.getenv("DS_API_BASE", ""))
        
        self.model_entry = tk.Entry(self.api_frame, width=20)
        self.model_entry.pack(side=tk.LEFT, padx=5)
        self.model_entry.insert(0, os.getenv("API_MODEL_NAME", ""))
        
        # 聊天显示区域
        self.chat_display = scrolledtext.ScrolledText(self.root, state='disabled', wrap=tk.WORD)
        self.chat_display.pack(pady=10, padx=10, expand=True, fill=tk.BOTH)
        
        # 消息输入区域
        self.input_frame = tk.Frame(self.root)
        self.input_frame.pack(pady=10, fill=tk.X)
        
        self.message_entry = tk.Entry(self.input_frame)
        self.message_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.message_entry.bind("<Return>", self.send_message)
        
        self.send_button = tk.Button(self.input_frame, text="发送", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_bar = tk.Label(self.root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def browse_server_script(self):
        """浏览服务器脚本文件"""
        initial_dir = os.path.dirname(DEFAULT_SERVER_PATH) if os.path.exists(DEFAULT_SERVER_PATH) else None
        filepath = filedialog.askopenfilename(
            title="选择服务器脚本",
            initialdir=initial_dir,
            filetypes=[("Python脚本", "*.py"), ("JavaScript脚本", "*.js"), ("所有文件", "*.*")]
        )
        if filepath:
            self.server_path_entry.delete(0, tk.END)
            self.server_path_entry.insert(0, filepath)
    
    def toggle_connection(self):
        """切换连接状态"""
        if self.running:
            self.loop.create_task(self.disconnect())
        else:
            self.loop.create_task(self.connect())
    
    async def connect(self):
        """连接到服务器"""
        server_path = self.server_path_entry.get().strip()
        if not server_path:
            messagebox.showerror("错误", "请输入服务器脚本路径")
            return
        
        try:
            # 更新API配置
            os.environ["DS_API_KEY"] = self.api_key_entry.get().strip()
            os.environ["DS_API_BASE"] = self.api_base_entry.get().strip()
            os.environ["API_MODEL_NAME"] = self.model_entry.get().strip()
            
            self.client = MCPClient()
            await self.client.connect(server_path)
            
            self.running = True
            self.connect_button.config(text="断开")
            self.server_path_entry.config(state='disabled')
            self.browse_button.config(state='disabled')
            self.api_key_entry.config(state='disabled')
            self.api_base_entry.config(state='disabled')
            self.model_entry.config(state='disabled')
            
            self.append_message("系统", f"已连接到服务器: {server_path}")
            self.update_status("已连接")
            
        except Exception as e:
            messagebox.showerror("连接错误", f"连接失败: {str(e)}")
            self.update_status(f"连接失败: {str(e)}")
    
    async def disconnect(self):
        """断开服务器连接"""
        try:
            if self.client:
                await self.client.cleanup()
                self.client = None
            
            self.running = False
            self.connect_button.config(text="连接")
            self.server_path_entry.config(state='normal')
            self.browse_button.config(state='normal')
            self.api_key_entry.config(state='normal')
            self.api_base_entry.config(state='normal')
            self.model_entry.config(state='normal')
            
            self.append_message("系统", "已断开服务器连接")
            self.update_status("已断开连接")
            
        except Exception as e:
            messagebox.showerror("断开错误", f"断开连接失败: {str(e)}")
            self.update_status(f"断开失败: {str(e)}")
    
    def send_message(self, event=None):
        """发送消息"""
        message = self.message_entry.get().strip()
        if message and self.client and self.running:
            self.loop.create_task(self._send_query(message))
            self.message_entry.delete(0, tk.END)
    
    async def _send_query(self, user_input: str):
        """异步发送查询并处理响应"""
        try:
            self.append_message("你", user_input)
            self.update_status("处理中...")
            
            # 禁用输入区域防止重复发送
            self.message_entry.config(state='disabled')
            self.send_button.config(state='disabled')
            
            response = await self.client.query(user_input)
            self.append_message("助手", response)
            
            self.update_status("就绪")
            
        except Exception as e:
            self.append_message("系统", f"处理查询时出错: {str(e)}")
            self.update_status(f"错误: {str(e)}")
            logger.error(f"处理查询时出错: {e}")
            
        finally:
            # 重新启用输入区域
            self.message_entry.config(state='normal')
            self.send_button.config(state='normal')
            self.message_entry.focus()
    
    def append_message(self, sender: str, message: str):
        """在聊天区域添加消息"""
        self.chat_display.config(state='normal')
        
        # 添加发送者标签
        self.chat_display.insert(tk.END, f"{sender}: ", "sender" if sender != "你" else "user")
        
        # 添加消息内容
        self.chat_display.insert(tk.END, f"{message}\n\n")
        
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
    
    def update_status(self, message: str):
        """更新状态栏"""
        self.status_bar.config(text=message)
    
    def run(self):
        """运行GUI主循环"""
        # 配置文本标签样式
        self.chat_display.tag_config("user", foreground="blue", font=('Arial', 10, 'bold'))
        self.chat_display.tag_config("sender", foreground="green", font=('Arial', 10, 'bold'))
        self.chat_display.tag_config("system", foreground="gray", font=('Arial', 9, 'italic'))
        
        async def run_async():
            while True:
                self.root.update()
                await asyncio.sleep(0.05)
        
        self.loop.run_until_complete(run_async())

def main():
    if len(sys.argv) < 2:
        root = tk.Tk()
        app = MCPClientGUI(root)
        app.run()
    else:
        # 保留原有的命令行功能
        async def cli_main():
            async with MCPClient() as client:
                await client.connect(sys.argv[1])
                await client.interactive_chat()
        
        asyncio.run(cli_main())

if __name__ == "__main__":
    main()