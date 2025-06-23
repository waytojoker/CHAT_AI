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

# 初始化对话历史
if "message" not in st.session_state:
    st.session_state["message"] = []

# Ollama 客户端
client = ollama.Client(host="http://127.0.0.1:11434")

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

#初始化选择模型
if "selected_service" not in st.session_state:
    st.session_state["selected_service"] = "Ollama"

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
        st.switch_page("pages/rag_main.py")  # 跳转到RAG页面
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

