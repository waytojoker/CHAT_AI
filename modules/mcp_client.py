import asyncio
import json
import logging
import re
import subprocess
import os
import signal
from typing import Dict, Any, List, Optional, Union, Callable
import httpx
from dataclasses import dataclass
import streamlit as st
import time
import tempfile
import shutil

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """MCP工具数据类"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


@dataclass
class MCPServerConfig:
    """MCP服务器配置数据类"""
    name: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    server_type: str = "process"  # "process", "http", "sse"


@dataclass
class MCPServer:
    """MCP服务器数据类"""
    name: str
    config: MCPServerConfig
    process: Optional[subprocess.Popen] = None
    url: Optional[str] = None
    tools: List[MCPTool] = None
    client: Optional[httpx.AsyncClient] = None


class MCPClient:
    """MCP客户端类，支持本地进程和远程连接"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.servers: Dict[str, MCPServer] = {}
        self.config_file = config_file
        self.temp_dir = None
        self.client = httpx.AsyncClient(timeout=30.0)
        
        if config_file:
            self.load_config(config_file)
    
    def load_config(self, config_file: str):
        """加载MCP配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info(f"加载MCP配置文件: {config_file}")
            
            # 处理MCP服务器配置
            mcp_servers = config.get("mcpServers", {})
            for server_name, server_config in mcp_servers.items():
                config_obj = MCPServerConfig(
                    name=server_name,
                    command=server_config.get("command"),
                    args=server_config.get("args", []),
                    env=server_config.get("env", {}),
                    url=server_config.get("url"),
                    server_type=server_config.get("server_type", "process")
                )
                
                # 创建服务器对象
                server = MCPServer(
                    name=server_name,
                    config=config_obj,
                    tools=[]
                )
                
                self.servers[server_name] = server
                logger.info(f"配置服务器: {server_name} (类型: {config_obj.server_type})")
        
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            raise e
    
    async def start_server(self, server_name: str) -> bool:
        """启动MCP服务器"""
        if server_name not in self.servers:
            logger.error(f"未找到服务器配置: {server_name}")
            return False
        
        server = self.servers[server_name]
        config = server.config
        
        try:
            if config.server_type == "process":
                return await self._start_process_server(server)
            elif config.server_type in ["http", "sse"]:
                return await self._start_remote_server(server)
            else:
                logger.error(f"不支持的服务器类型: {config.server_type}")
                return False
                
        except Exception as e:
            logger.error(f"启动服务器失败 {server_name}: {str(e)}")
            return False
    
    async def _start_process_server(self, server: MCPServer) -> bool:
        """启动本地进程服务器"""
        config = server.config
        
        try:
            # 创建临时目录用于进程间通信
            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp(prefix="mcp_")
            
            # 设置环境变量
            env = os.environ.copy()
            env.update(config.env or {})
            
            # 启动进程，启用双向通信
            process = subprocess.Popen(
                [config.command] + (config.args or []),
                env=env,
                cwd=self.temp_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            server.process = process
            logger.info(f"启动进程服务器: {server.name} (PID: {process.pid})")
            
            # 等待服务器启动
            await asyncio.sleep(3)
            
            # 检查进程是否还在运行
            if process.poll() is None:
                # 尝试获取工具列表
                tools = await self._get_process_tools(server)
                server.tools = tools
                logger.info(f"进程服务器启动成功: {server.name}，工具数量: {len(tools)}")
                return True
            else:
                # 进程已退出
                stdout, stderr = process.communicate()
                logger.error(f"进程服务器启动失败: {server.name}")
                logger.error(f"stdout: {stdout}")
                logger.error(f"stderr: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"启动进程服务器失败: {str(e)}")
            return False
    
    async def _start_remote_server(self, server: MCPServer) -> bool:
        """启动远程服务器连接"""
        config = server.config
        
        try:
            if not config.url:
                logger.error(f"远程服务器缺少URL配置: {server.name}")
                return False
            
            server.url = config.url
            server.client = httpx.AsyncClient(timeout=30.0)
            
            # 测试连接
            if await self._test_remote_connection(server):
                # 获取工具列表
                tools = await self._get_remote_tools(server)
                server.tools = tools
                logger.info(f"远程服务器连接成功: {server.name}")
                return True
            else:
                logger.error(f"远程服务器连接失败: {server.name}")
                return False
                
        except Exception as e:
            logger.error(f"启动远程服务器失败: {str(e)}")
            return False
    
    async def _test_remote_connection(self, server: MCPServer) -> bool:
        """测试远程服务器连接"""
        try:
            if server.config.server_type == "http":
                response = await server.client.get(f"{server.url}/health")
                return response.status_code == 200
            elif server.config.server_type == "sse":
                response = await server.client.get(server.url, timeout=5.0)
                return response.status_code == 200
            return False
        except Exception as e:
            logger.warning(f"连接测试失败: {str(e)}")
            return False
    
    async def _get_process_tools(self, server: MCPServer) -> List[MCPTool]:
        """从进程服务器获取工具列表"""
        try:
            # 通过标准输入输出与进程通信
            if not server.process:
                return []
            
            # 发送工具列表请求
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            try:
                # 写入请求到进程
                request_str = json.dumps(request) + "\n"
                server.process.stdin.write(request_str)
                server.process.stdin.flush()
                
                # 读取响应，设置超时
                import select
                import time
                
                start_time = time.time()
                timeout = 10.0  # 10秒超时
                
                while time.time() - start_time < timeout:
                    # 检查是否有可读数据
                    if select.select([server.process.stdout], [], [], 0.1)[0]:
                        response_line = server.process.stdout.readline()
                        if response_line:
                            try:
                                response = json.loads(response_line.strip())
                                logger.info(f"收到进程响应: {response}")
                                
                                if "result" in response and "tools" in response["result"]:
                                    tools = []
                                    for tool_data in response["result"]["tools"]:
                                        tool = MCPTool(
                                            name=tool_data["name"],
                                            description=tool_data["description"],
                                            inputSchema=tool_data.get("inputSchema", {})
                                        )
                                        tools.append(tool)
                                    return tools
                                elif "error" in response:
                                    logger.error(f"进程返回错误: {response['error']}")
                                    break
                            except json.JSONDecodeError as e:
                                logger.warning(f"无法解析进程响应: {response_line.strip()}, 错误: {e}")
                                continue
                    
                    # 检查进程是否还在运行
                    if server.process.poll() is not None:
                        logger.error("进程已退出")
                        break
                
                logger.warning("获取工具列表超时")
                return []
                
            except Exception as e:
                logger.error(f"与进程通信失败: {str(e)}")
                return []
            
        except Exception as e:
            logger.error(f"获取进程工具列表失败: {str(e)}")
            return []
    
    async def _get_remote_tools(self, server: MCPServer) -> List[MCPTool]:
        """从远程服务器获取工具列表"""
        try:
            if server.config.server_type == "http":
                response = await server.client.get(f"{server.url}/tools")
                if response.status_code == 200:
                    data = response.json()
                    tools = []
                    for tool_data in data.get("tools", []):
                        tool = MCPTool(
                            name=tool_data["name"],
                            description=tool_data["description"],
                            inputSchema=tool_data.get("inputSchema", {})
                        )
                        tools.append(tool)
                    return tools
            
            elif server.config.server_type == "sse":
                # 尝试多种方式获取SSE工具列表
                return await self._get_sse_tools(server.url, server.client)
            
            return []
            
        except Exception as e:
            logger.error(f"获取远程工具列表失败: {str(e)}")
            return []
    
    async def _get_sse_tools(self, url: str, client: httpx.AsyncClient) -> List[MCPTool]:
        """获取SSE服务器工具列表"""
        try:
            headers = {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
            
            # 方法1: 直接GET请求
            try:
                response = await client.get(url, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    content = response.text
                    tools = self._parse_sse_response_for_tools(content)
                    if tools:
                        return tools
            except Exception as e:
                logger.warning(f"直接GET获取SSE工具失败: {str(e)}")
            
            # 方法2: 通过query参数
            try:
                tools_url = f"{url}?method=tools/list"
                response = await client.get(tools_url, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    content = response.text
                    tools = self._parse_sse_response_for_tools(content)
                    if tools:
                        return tools
            except Exception as e:
                logger.warning(f"query参数获取SSE工具失败: {str(e)}")
            
            return []
            
        except Exception as e:
            logger.error(f"获取SSE工具列表失败: {str(e)}")
            return []
    
    def _parse_sse_response_for_tools(self, content: str) -> List[MCPTool]:
        """解析SSE响应中的工具信息"""
        tools = []
        try:
            lines = content.strip().split('\n')
            for line in lines:
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if "result" in data and "tools" in data["result"]:
                            for tool_data in data["result"]["tools"]:
                                tool = MCPTool(
                                    name=tool_data["name"],
                                    description=tool_data["description"],
                                    inputSchema=tool_data.get("inputSchema", {})
                                )
                                tools.append(tool)
                        elif "tools" in data:
                            for tool_data in data["tools"]:
                                tool = MCPTool(
                                    name=tool_data["name"],
                                    description=tool_data["description"],
                                    inputSchema=tool_data.get("inputSchema", {})
                                )
                                tools.append(tool)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"解析SSE响应失败: {str(e)}")
        
        return tools
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        if server_name not in self.servers:
            raise ValueError(f"未找到MCP服务器: {server_name}")
        
        server = self.servers[server_name]
        
        try:
            if server.config.server_type == "process":
                return await self._call_process_tool(server, tool_name, arguments)
            elif server.config.server_type == "http":
                return await self._call_http_tool(server, tool_name, arguments)
            elif server.config.server_type == "sse":
                return await self._call_sse_tool(server, tool_name, arguments)
            else:
                raise ValueError(f"不支持的服务器类型: {server.config.server_type}")
            
        except Exception as e:
            logger.error(f"调用工具失败 {tool_name} 于服务器 {server_name}: {str(e)}")
            raise e
    
    async def _call_process_tool(self, server: MCPServer, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用进程服务器工具"""
        try:
            if not server.process:
                raise Exception("进程服务器未启动")
            
            # 构建请求
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            try:
                # 发送请求
                request_str = json.dumps(request) + "\n"
                server.process.stdin.write(request_str)
                server.process.stdin.flush()
                
                # 读取响应，设置超时
                import select
                import time
                
                start_time = time.time()
                timeout = 30.0  # 30秒超时
                
                while time.time() - start_time < timeout:
                    # 检查是否有可读数据
                    if select.select([server.process.stdout], [], [], 0.1)[0]:
                        response_line = server.process.stdout.readline()
                        if response_line:
                            try:
                                response = json.loads(response_line.strip())
                                logger.info(f"收到工具调用响应: {response}")
                                
                                if "result" in response:
                                    return response["result"]
                                elif "error" in response:
                                    raise Exception(f"工具调用错误: {response['error']}")
                            except json.JSONDecodeError as e:
                                logger.warning(f"无法解析工具调用响应: {response_line.strip()}, 错误: {e}")
                                continue
                    
                    # 检查进程是否还在运行
                    if server.process.poll() is not None:
                        raise Exception("进程已退出")
                
                raise Exception("工具调用超时")
                
            except Exception as e:
                logger.error(f"与进程通信失败: {str(e)}")
                raise e
            
        except Exception as e:
            logger.error(f"调用进程工具失败: {str(e)}")
            raise e
    
    async def _call_http_tool(self, server: MCPServer, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用HTTP服务器工具"""
        try:
            request_data = {
                "tool": tool_name,
                "arguments": arguments
            }
            
            response = await server.client.post(
                f"{server.url}/call_tool",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result
            
        except Exception as e:
            logger.error(f"调用HTTP工具失败: {str(e)}")
            raise e
    
    async def _call_sse_tool(self, server: MCPServer, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用SSE服务器工具"""
        try:
            # 构建请求URL
            import urllib.parse
            params = {
                "method": "tools/call",
                "tool": tool_name,
                "arguments": json.dumps(arguments)
            }
            query_string = urllib.parse.urlencode(params)
            call_url = f"{server.url}?{query_string}"
            
            headers = {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
            
            # 发送请求并读取响应
            async with server.client.stream('GET', call_url, headers=headers, timeout=30.0) as response:
                if response.status_code != 200:
                    raise Exception(f"SSE工具调用失败，状态码: {response.status_code}")
                
                content_chunks = []
                async for chunk in response.aiter_text():
                    content_chunks.append(chunk)
                
                content = ''.join(content_chunks)
                result = self._parse_sse_tool_response(content)
                return result
                
        except Exception as e:
            logger.error(f"调用SSE工具失败: {str(e)}")
            raise e
    
    def _parse_sse_tool_response(self, content: str) -> Dict[str, Any]:
        """解析SSE工具调用响应"""
        try:
            # 解析SSE格式
            lines = content.strip().split('\n')
            current_event = {}
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    if current_event and 'data' in current_event:
                        try:
                            data = json.loads(current_event['data'])
                            if "result" in data:
                                return data["result"]
                            elif "error" in data:
                                raise Exception(f"工具调用错误: {data['error']}")
                            else:
                                return data
                        except json.JSONDecodeError:
                            return {"content": current_event['data']}
                    
                    current_event = {}
                    continue
                
                if line.startswith('data: '):
                    data = line[6:]
                    if 'data' in current_event:
                        current_event['data'] += '\n' + data
                    else:
                        current_event['data'] = data
            
            # 处理最后一个事件
            if current_event and 'data' in current_event:
                try:
                    data = json.loads(current_event['data'])
                    if "result" in data:
                        return data["result"]
                    elif "error" in data:
                        raise Exception(f"工具调用错误: {data['error']}")
                    else:
                        return data
                except json.JSONDecodeError:
                    return {"content": current_event['data']}
            
            # 尝试解析整个内容为JSON
            try:
                data = json.loads(content)
                if "result" in data:
                    return data["result"]
                elif "error" in data:
                    raise Exception(f"工具调用错误: {data['error']}")
                else:
                    return data
            except json.JSONDecodeError:
                pass
            
            # 返回原始内容
            if content.strip():
                return {"content": content.strip()}
            
            return {}
                
        except Exception as e:
            logger.error(f"解析SSE工具响应失败: {str(e)}")
            return {"error": str(e), "raw_content": content[:500]}
    
    def get_available_tools(self, server_name: str = None) -> Dict[str, List[MCPTool]]:
        """获取可用工具列表"""
        if server_name:
            if server_name in self.servers:
                return {server_name: self.servers[server_name].tools or []}
            else:
                return {}
        
        result = {}
        for name, server in self.servers.items():
            result[name] = server.tools or []
        
        return result
    
    def get_servers(self) -> Dict[str, MCPServer]:
        """获取所有服务器"""
        return self.servers
    
    async def stop_server(self, server_name: str) -> bool:
        """停止服务器"""
        if server_name not in self.servers:
            return False
        
        server = self.servers[server_name]
        
        try:
            if server.process:
                # 停止进程
                server.process.terminate()
                try:
                    server.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.process.kill()
                    server.process.wait()
                
                logger.info(f"停止进程服务器: {server_name}")
            
            if server.client:
                # 关闭HTTP客户端
                await server.client.aclose()
                logger.info(f"关闭远程服务器连接: {server_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"停止服务器失败 {server_name}: {str(e)}")
            return False
    
    async def stop_all_servers(self):
        """停止所有服务器"""
        for server_name in list(self.servers.keys()):
            await self.stop_server(server_name)
    
    async def close(self):
        """关闭客户端"""
        await self.stop_all_servers()
        await self.client.aclose()
        
        # 清理临时目录
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


class MCPToolCaller:
    """MCP工具调用器，集成到对话流程中"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    async def parse_and_execute_tools(self, text: str) -> List[Dict[str, Any]]:
        """解析文本中的工具调用并执行"""
        tool_calls = self._parse_tool_calls_from_text(text)
        results = []
        
        for tool_call in tool_calls:
            try:
                result = await self.mcp_client.call_tool(
                    tool_call["server"],
                    tool_call["tool"],
                    tool_call["arguments"]
                )
                results.append({
                    "success": True,
                    "tool": tool_call["tool"],
                    "server": tool_call["server"],
                    "result": result
                })
            except Exception as e:
                results.append({
                    "success": False,
                    "tool": tool_call["tool"],
                    "server": tool_call["server"],
                    "error": str(e)
                })
        
        return results
    
    def _parse_tool_calls_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中解析工具调用"""
        tool_calls = []
        
        # 格式1: @tool:server_name:tool_name{arguments_json}
        pattern1 = r'@tool:([^:]+):([^{]+)\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
        matches1 = re.findall(pattern1, text)
        
        for match in matches1:
            server_name = match[0].strip()
            tool_name = match[1].strip()
            try:
                arguments = json.loads(match[2])
                tool_calls.append({
                    "server": server_name,
                    "tool": tool_name,
                    "arguments": arguments
                })
            except json.JSONDecodeError:
                try:
                    arguments = self._parse_simple_arguments(match[2])
                    tool_calls.append({
                        "server": server_name,
                        "tool": tool_name,
                        "arguments": arguments
                    })
                except Exception as e:
                    logger.error(f"无法解析工具调用参数: {match[2]}, 错误: {e}")
        
        # 格式2: JSON格式的工具调用
        pattern2 = r'\{"tool_call":\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}\}'
        matches2 = re.findall(pattern2, text)
        
        for match in matches2:
            try:
                tool_call_data = json.loads(match)
                if "tool_call" in tool_call_data:
                    call_info = tool_call_data["tool_call"]
                    tool_calls.append({
                        "server": call_info.get("server", ""),
                        "tool": call_info.get("tool", ""),
                        "arguments": call_info.get("arguments", {})
                    })
            except json.JSONDecodeError as e:
                logger.error(f"无法解析JSON工具调用: {match}, 错误: {e}")
        
        return tool_calls
    
    def _parse_simple_arguments(self, arg_string: str) -> Dict[str, Any]:
        """解析简单的参数字符串，支持 key=value 格式"""
        arguments = {}
        
        pairs = arg_string.split(',')
        for pair in pairs:
            pair = pair.strip()
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if value.startswith('"') and value.endswith('"'):
                    arguments[key] = value[1:-1]
                elif value.lower() in ['true', 'false']:
                    arguments[key] = value.lower() == 'true'
                elif value.isdigit():
                    arguments[key] = int(value)
                elif value.replace('.', '').isdigit():
                    arguments[key] = float(value)
                else:
                    arguments[key] = value
            else:
                arguments['query'] = pair
        
        return arguments
    
    def format_tool_result(self, results: List[Dict[str, Any]]) -> str:
        """格式化工具执行结果"""
        if not results:
            return ""
        
        formatted_results = []
        for result in results:
            if result["success"]:
                formatted_results.append(
                    f"✅ 工具 {result['tool']} (服务器: {result['server']}) 执行成功:\n"
                    f"结果: {json.dumps(result['result'], ensure_ascii=False, indent=2)}"
                )
            else:
                formatted_results.append(
                    f"❌ 工具 {result['tool']} (服务器: {result['server']}) 执行失败:\n"
                    f"错误: {result['error']}"
                )
        
        return "\n\n".join(formatted_results)
    
    def get_tools_description_for_ai(self) -> str:
        """获取工具描述，用于AI自主选择工具"""
        all_tools = self.mcp_client.get_available_tools()
        
        if not any(tools for tools in all_tools.values()):
            return ""
        
        description = "以下是可用的工具列表，当需要获取外部信息或执行特定任务时可以调用：\n\n"
        
        for server_name, tools in all_tools.items():
            if tools:
                description += f"**{server_name}服务器的工具：**\n"
                for tool in tools:
                    description += f"- `{tool.name}`: {tool.description}\n"
                    if tool.inputSchema and "properties" in tool.inputSchema:
                        params = ", ".join(tool.inputSchema["properties"].keys())
                        description += f"  参数: {params}\n"
                description += "\n"
        
        description += """调用工具时，请使用以下JSON格式：
{"tool_call": {"server": "服务器名", "tool": "工具名", "arguments": {"参数名": "参数值"}}}

例如：
{"tool_call": {"server": "knowledge-base", "tool": "search", "arguments": {"query": "人工智能发展趋势"}}}

注意：只有当确实需要外部信息或工具帮助时才调用工具。
"""
        
        return description


# 同步包装器，用于在Streamlit中使用
def run_async_function(coro):
    """在Streamlit中运行异步函数的包装器"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro) 