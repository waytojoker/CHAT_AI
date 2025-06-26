import time
import ollama
import streamlit as st
import re
# 导入模块file_processing
from modules import file_processing
from modules.conversation_display import display_conversation
from modules.history_module import show_conversation_history
import requests
from modules.model_service import create_model_service  # 导入模型服务工厂
# 导入MCP客户端相关模块
from modules.mcp_client import MCPClient, MCPToolCaller, run_async_function, MCPServerConfig, MCPServer
import asyncio
import json

# 设置页面标题（标签页标题）
st.set_page_config(page_title="智联未来-智能助手", page_icon="🤖",
initial_sidebar_state = "collapsed",  # 默认隐藏 或 "dexpanded"
menu_items = None  # 隐藏自动导航1
)
# 隐藏自动导航2
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

maxHistoryMessages = 10

from modules.xhs_prompt import (
    XHS_ROLE_CONFIG,
    XHS_SCENE_CONFIG,
    XHS_TASK_CONFIG,
)
from modules.gzh_prompt import (
    GZH_ROLE_CONFIG,
    GZH_SCENE_CONFIG,
    GZH_TASK_CONFIG,
)
# Ollama 客户端
client = ollama.Client(host="http://127.0.0.1:11434")
def init():
    # 初始化对话历史
    if "message" not in st.session_state:
        st.session_state["message"] = []

    # 初始化配置参数
    if "role_config" not in st.session_state:
        st.session_state['role_config'] = "你是一个智能助手，能够回答各种问题并提供帮助。"

    if "scene_config" not in st.session_state:
        st.session_state['scene_config'] = "在一个友好、专业的对话环境中"

    if "task_config" not in st.session_state:
        st.session_state['task_config'] = "请根据用户的问题提供准确、有用的回答"

    if "temperature" not in st.session_state:
        st.session_state['temperature'] = 0.7

    if "conversation_id" not in st.session_state:
        st.session_state['conversation_id'] = None

    # 初始化历史记录显示状态
    if "show_history" not in st.session_state:
        st.session_state["show_history"] = False

    # 初始化选择模型
    if "selected_service" not in st.session_state:
        st.session_state["selected_service"] = "Ollama"

    # 初始化MCP相关状态
    if "mcp_client" not in st.session_state:
        st.session_state["mcp_client"] = MCPClient()

    if "mcp_tool_caller" not in st.session_state:
        st.session_state["mcp_tool_caller"] = MCPToolCaller(st.session_state["mcp_client"])

    if "enable_mcp" not in st.session_state:
        st.session_state["enable_mcp"] = False

    if "mcp_servers" not in st.session_state:
        st.session_state["mcp_servers"] = []

    if "auto_tool_mode" not in st.session_state:
        st.session_state["auto_tool_mode"] = True

init()

# 自动配置MCP服务器（如果还没有配置）
if "mcp_auto_configured" not in st.session_state:
    st.session_state["mcp_auto_configured"] = False

if not st.session_state["mcp_auto_configured"]:
    try:
        # 自动配置knowledge-base服务器
        config_obj = MCPServerConfig(
            name="knowledge-base",
            command="node",
            args=["dist/index.js"],
            env={},
            server_type="process"
        )
        
        server = MCPServer(
            name="knowledge-base",
            config=config_obj,
            tools=[]
        )
        
        # 添加到客户端
        st.session_state["mcp_client"].servers["knowledge-base"] = server
        
        # 启动服务器
        if run_async_function(st.session_state["mcp_client"].start_server("knowledge-base")):
            st.session_state["mcp_auto_configured"] = True
            print("✅ 自动配置并启动knowledge-base服务器成功")
        else:
            print("❌ 自动启动knowledge-base服务器失败")
            
    except Exception as e:
        print(f"❌ 自动配置MCP服务器失败: {str(e)}")
        st.session_state["mcp_auto_configured"] = True  # 避免重复尝试

def get_system_prompt():
    """构建系统提示词"""
    return f"""角色设定：{st.session_state['role_config']}

场景设定：{st.session_state['scene_config']}

任务要求：{st.session_state['task_config']}

请根据以上设定进行对话。"""


#  文件处理
uploaded_files = []
file_content = ""

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置设置")

    # 历史记录和新建对话按钮
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📖 历史记录", key="history_button"):
            st.session_state["show_history"] = not st.session_state["show_history"]  # 切换历史记录显示状态
    with col2:
        if st.button("📝 新建对话", key="new_conversation_button"):
            response = requests.post(f"http://127.0.0.1:5000/new_conversation", json={"user_id": 1})
            if response.status_code == 200:
                st.session_state["conversation_id"] = response.json()["conversation_id"]
                st.session_state["message"] = []
                st.session_state["show_history"] = False
                st.rerun()
            else:
                st.error("新建对话失败")

    # 文件处理部分
    st.subheader("☁️ 上传文件")
    # 文件处理
    if 'file_content' not in st.session_state:
        st.session_state['file_content'] = ""

    # 侧边栏配置
    with st.sidebar:
        # 文件处理部分
        uploaded_files = st.file_uploader("上传文件", type=["docx", "pdf", "png", "jpg", "txt", "xlsx", "pptx"],
                                          accept_multiple_files=True)
        if uploaded_files:
            st.session_state['file_content'] = file_processing.get_file_content(uploaded_files)
            st.success(f"已成功加载 {len(uploaded_files)} 个文件内容")

    # ===== 新增的RAG增强功能入口 =====
    st.subheader("🔍 RAG增强功能")
    if st.button("🚀 开启RAG增强对话", key="rag_button"):
        st.session_state.clear()
        st.switch_page("pages/rag_main.py")  # 跳转到RAG页面
    st.divider()  # 分隔线
    
    # ===== MCP工具调用功能 =====
    st.subheader("🛠️ MCP工具调用")
    st.session_state["enable_mcp"] = st.checkbox("启用MCP工具调用", value=st.session_state["enable_mcp"])
    
    if st.session_state["enable_mcp"]:
        # 添加自主调用模式选择
        st.subheader("🤖 调用模式")
        auto_mode = st.radio(
            "选择工具调用模式",
            ["AI自主选择工具", "手动指定工具"],
            index=0,
            help="AI自主选择：模型会根据对话内容自动决定是否使用工具\n手动指定：需要使用特定语法手动调用工具"
        )
        st.session_state["auto_tool_mode"] = (auto_mode == "AI自主选择工具")
    
    if st.session_state["enable_mcp"]:
        # MCP服务器管理
        with st.expander("MCP服务器管理", expanded=False):
            st.write("**从JSON配置导入MCP服务器**")
            
            # JSON配置输入对话框
            json_config = st.text_area(
                "粘贴MCP服务器配置JSON",
                placeholder='''示例格式：
{
  "mcpServers": {
    "knowledge-base": {
      "command": "node",
      "args": ["dist/index.js"],
      "env": {}
    },
    "weather-service": {
      "url": "https://api.weatherapi.com/v1",
      "type": "http"
    }
  }
}''',
                height=200,
                key="mcp_json_config"
            )
            
            if st.button("导入配置文件", key="import_config_file"):
                if json_config.strip():
                    try:
                        config = json.loads(json_config)
                        
                        if "mcpServers" in config:
                            success_count = 0
                            for name, server_config in config["mcpServers"].items():
                                try:
                                    # 根据配置类型处理
                                    if "command" in server_config:
                                        # 本地进程服务器
                                        config_obj = MCPServerConfig(
                                            name=name,
                                            command=server_config["command"],
                                            args=server_config.get("args", []),
                                            env=server_config.get("env", {}),
                                            server_type="process"
                                        )
                                    elif "url" in server_config:
                                        # 远程服务器
                                        server_type = server_config.get("type", "http")
                                        config_obj = MCPServerConfig(
                                            name=name,
                                            url=server_config["url"],
                                            server_type=server_type
                                        )
                                    else:
                                        st.warning(f"跳过服务器 {name}：配置格式不支持")
                                        continue
                                    
                                    # 创建服务器对象
                                    server = MCPServer(
                                        name=name,
                                        config=config_obj,
                                        tools=[]
                                    )
                                    
                                    # 先将服务器添加到客户端
                                    st.session_state["mcp_client"].servers[name] = server
                                    
                                    # 然后启动服务器
                                    if run_async_function(st.session_state["mcp_client"].start_server(name)):
                                        success_count += 1
                                    else:
                                        # 如果启动失败，从客户端中移除
                                        if name in st.session_state["mcp_client"].servers:
                                            del st.session_state["mcp_client"].servers[name]
                                    
                                except Exception as e:
                                    st.warning(f"导入服务器 {name} 失败: {str(e)}")
                            
                            if success_count > 0:
                                st.success(f"✅ 成功导入并启动 {success_count} 个MCP服务器")
                                st.rerun()
                            else:
                                st.error("❌ 没有成功导入任何服务器")
                        else:
                            st.error("❌ JSON格式错误：缺少 'mcpServers' 字段")
                    
                    except json.JSONDecodeError as e:
                        st.error(f"❌ JSON格式错误: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ 配置文件处理失败: {str(e)}")
                else:
                    st.error("请输入JSON配置")
            
            # 显示现有服务器
            servers = st.session_state["mcp_client"].get_servers()
            if servers:
                st.write("**已连接的服务器**")
                for name, server in servers.items():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"**{name}**")
                        st.caption("MCP服务器")
                    with col2:
                        st.caption(f"类型: {server.config.server_type.upper()}")
                        if server.config.url:
                            st.caption(f"URL: {server.config.url}")
                        if server.config.command:
                            st.caption(f"命令: {server.config.command}")
                        tools_count = len(server.tools) if server.tools else 0
                        st.caption(f"可用工具: {tools_count}个")
                    with col3:
                        if st.button("停止", key=f"stop_{name}"):
                            run_async_function(st.session_state["mcp_client"].stop_server(name))
                            st.rerun()
                
                # 显示可用工具
                all_tools = st.session_state["mcp_client"].get_available_tools()
                if any(tools for tools in all_tools.values()):
                    st.write("**可用工具**")
                    for server_name, tools in all_tools.items():
                        if tools:
                            st.write(f"*{server_name}服务器:*")
                            for tool in tools:
                                st.write(f"  • `{tool.name}`: {tool.description}")
                
    
    st.divider()  # 分隔线
    
    # 优先显示模型选择和流式开关
    st.subheader("🤖 模型与响应配置")
    # 模型选择
    models = ["deepseek-r1:7b", "deepseek-r1:1.5b","ernie-speed-128k(无流式API)"]  # 可以根据需要添加更多模型
    selected_model = st.selectbox("选择模型", models)
    # 流式开关
    use_stream = st.checkbox("使用流式响应", value=True)

    # Prompt配置
    st.subheader("📝 Prompt配置")

    # 角色配置
    st.session_state['role_config'] = st.text_area(
        "角色配置",
        value=st.session_state['role_config'],
        height=100,
        help="定义AI助手的角色和身份"
    )

    # 场景配置
    st.session_state['scene_config'] = st.text_area(
        "场景配置",
        value=st.session_state['scene_config'],
        height=80,
        help="设定对话的场景和环境"
    )

    # 任务配置
    st.session_state['task_config'] = st.text_area(
        "任务配置",
        value=st.session_state['task_config'],
        height=80,
        help="明确AI助手需要完成的任务"
    )

    template = st.selectbox("📋选择任务模板", ["自定义", "小红书文案生成", "公众号错字识别"])
    if st.button("确定", key="template_confirm"):
        if template == "小红书文案生成":
            # 更新配置为小红书文案的设置
            st.session_state['role_config'] = XHS_ROLE_CONFIG
            st.session_state['scene_config'] = XHS_SCENE_CONFIG
            st.session_state['task_config'] = XHS_TASK_CONFIG
        elif template == "公众号错字识别":
            # 更新配置为公众号错字检查的设置
            st.session_state['role_config'] = GZH_ROLE_CONFIG
            st.session_state['scene_config'] = GZH_SCENE_CONFIG
            st.session_state['task_config'] = GZH_TASK_CONFIG
        st.rerun()
    st.divider()

    # 参数配置
    st.subheader("🎛️ 参数配置")

    # Temperature配置
    st.session_state['temperature'] = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=st.session_state['temperature'],
        step=0.1,
        help="控制回答的创造性。值越高越有创意，值越低越保守"
    )

    # 显示当前配置预览
    with st.expander("📋 当前配置预览"):
        st.text("系统提示词:")
        st.text(get_system_prompt())
        st.text(f"Temperature: {st.session_state['temperature']}")

    # 重置配置按钮
    if st.button("🔄 重置为默认配置"):
        st.session_state['role_config'] = "你是一个智能助手，能够回答各种问题并提供帮助。"
        st.session_state['scene_config'] = "在一个友好、专业的对话环境中"
        st.session_state['task_config'] = "请根据用户的问题提供准确、有用的回答"
        st.session_state['temperature'] = 0.7
        st.rerun()

    # 清空对话历史按钮
    if st.button("🗑️ 清空对话历史"):
        st.session_state["message"] = []
        st.rerun()

# 显示当前配置状态
col1, col2 = st.columns([3, 1])
with col2:
    st.caption(f"🌡️ Temperature: {st.session_state['temperature']}")

st.title("智联未来")
st.divider()  # 分割线

conversation_id = None
# 显示历史记录
if (st.session_state["show_history"] == True):
    conversation_id = show_conversation_history(user_id=1, show_history=True)
    st.session_state["conversation_id"] = conversation_id
    if (conversation_id):
        # 显示先前消息
        for message in st.session_state["message"]:
            content = message["content"]
            if message["role"] == "user" and "用户提问：" in content:
                content = content.split("用户提问：")[-1]
            st.chat_message(message["role"]).markdown(content)
elif st.session_state["conversation_id"]:
    conversation_id = st.session_state["conversation_id"]

prompt = st.chat_input("请输入你的问题：")

# 调用封装的对话展示逻辑
if prompt:
    if conversation_id:
        display_conversation(
            prompt=prompt,
            file_content=st.session_state.get('file_content', ''),
            client=client,
            selected_model=selected_model,
            use_stream=use_stream,
            maxHistoryMessages=maxHistoryMessages,
            conversation_id=conversation_id,
            user_id=1,
        )
    else:
        conversation_id = display_conversation(
            prompt=prompt,
            file_content=st.session_state.get('file_content', ''),
            client=client,
            selected_model=selected_model,
            use_stream=use_stream,
            maxHistoryMessages=maxHistoryMessages,
        )

