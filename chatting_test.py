import time
import streamlit as st
import re
from modules import file_processing
from modules.conversation_display import display_conversation
from modules.history_module import show_conversation_history
import requests
from model_service import create_model_service  # 导入模型服务工厂

# 设置页面标题
st.set_page_config(page_title="智联未来-智能助手", page_icon="🤖")
maxHistoryMessages = 10

# 导入模板配置
from modules.xhs_prompt import XHS_ROLE_CONFIG, XHS_SCENE_CONFIG, XHS_TASK_CONFIG
from modules.gzh_prompt import GZH_ROLE_CONFIG, GZH_SCENE_CONFIG, GZH_TASK_CONFIG


# 初始化会话状态
def init_session_state():
    session_vars = {
        "message": [],
        "model_service": None,
        'role_config': "你是一个智能助手，能够回答各种问题并提供帮助。",
        'scene_config': "在一个友好、专业的对话环境中",
        'task_config': "请根据用户的问题提供准确、有用的回答",
        'temperature': 0.7,
        'conversation_id': None,
        "show_history": False,
        'file_content': "",
        'selected_service': "Ollama"  # 新增服务类型状态
    }
    for key, value in session_vars.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


def get_system_prompt():
    return f"""角色设定：{st.session_state['role_config']}
场景设定：{st.session_state['scene_config']}
任务要求：{st.session_state['task_config']}"""


# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置设置")

    # 操作按钮
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📖 历史记录"):
            st.session_state["show_history"] = not st.session_state["show_history"]
    with col2:
        if st.button("📝 新建对话"):
            response = requests.post("http://127.0.0.1:5000/new_conversation", json={"user_id": 1})
            if response.status_code == 200:
                st.session_state.update({
                    "conversation_id": response.json()["conversation_id"],
                    "message": [],
                    "show_history": False
                })
                st.rerun()
            else:
                st.error("新建对话失败")

    # 文件上传
    st.subheader("☁️ 上传文件")
    uploaded_files = st.file_uploader(
        "上传文件",
        type=["docx", "pdf", "png", "jpg", "txt", "xlsx", "pptx"],
        accept_multiple_files=True
    )
    if uploaded_files:
        st.session_state['file_content'] = file_processing.get_file_content(uploaded_files)
        st.success(f"已加载 {len(uploaded_files)} 个文件")

    # 模型配置
    st.subheader("🤖 模型配置")

    # 服务类型选择
    st.session_state['selected_service'] = st.selectbox(
        "选择服务类型",
        ["Ollama", "Qianfan"],
        index=0 if st.session_state['selected_service'] == "Ollama" else 1
    )

    # Ollama配置
    if st.session_state['selected_service'] == "Ollama":
        ollama_host = st.text_input("Ollama服务地址", value="http://127.0.0.1:11434")
        ollama_models = ["deepseek-r1:7b", "deepseek-r1:1.5b"]  # 包含原有两个deepseek模型
        selected_model = st.selectbox("选择模型", ollama_models)

        if st.button("连接Ollama服务"):
            try:
                st.session_state["model_service"] = create_model_service(
                    service_type="ollama",
                    host=ollama_host,
                    model=selected_model
                )
                st.success(f"{selected_model} 连接成功")
            except Exception as e:
                st.error(f"连接失败: {str(e)}")

    # 千帆配置
    elif st.session_state['selected_service'] == "Qianfan":
        qianfan_auth = st.text_input("千帆授权令牌", type="password")
        qianfan_models = ["ernie-4.5-turbo-vl-32k", "ernie-3.5"]
        selected_model = st.selectbox("千帆模型", qianfan_models)

        if st.button("连接千帆服务"):
            try:
                st.session_state["model_service"] = create_model_service(
                    service_type="qianfan",
                    authorization=qianfan_auth,
                    model=selected_model
                )
                st.success(f"{selected_model} 连接成功")
            except Exception as e:
                st.error(f"连接失败: {str(e)}")

    # 流式响应开关
    use_stream = st.checkbox("使用流式响应", value=True)

    # Prompt配置
    st.subheader("📝 Prompt配置")
    st.session_state['role_config'] = st.text_area("角色配置", value=st.session_state['role_config'], height=100)
    st.session_state['scene_config'] = st.text_area("场景配置", value=st.session_state['scene_config'], height=80)
    st.session_state['task_config'] = st.text_area("任务配置", value=st.session_state['task_config'], height=80)

    # 模板选择
    template = st.selectbox("📋 选择任务模板", ["自定义", "小红书文案生成", "公众号错字识别"])
    if st.button("应用模板"):
        if template == "小红书文案生成":
            st.session_state.update({
                'role_config': XHS_ROLE_CONFIG,
                'scene_config': XHS_SCENE_CONFIG,
                'task_config': XHS_TASK_CONFIG
            })
        elif template == "公众号错字识别":
            st.session_state.update({
                'role_config': GZH_ROLE_CONFIG,
                'scene_config': GZH_SCENE_CONFIG,
                'task_config': GZH_TASK_CONFIG
            })
        st.rerun()

    # 参数配置
    st.subheader("🎛️ 参数配置")
    st.session_state['temperature'] = st.slider("Temperature", 0.0, 2.0, st.session_state['temperature'], 0.1)

    # 操作按钮
    if st.button("🔄 重置配置"):
        st.session_state.update({
            'role_config': "你是一个智能助手，能够回答各种问题并提供帮助。",
            'scene_config': "在一个友好、专业的对话环境中",
            'task_config': "请根据用户的问题提供准确、有用的回答",
            'temperature': 0.7
        })
        st.rerun()

    if st.button("🗑️ 清空历史"):
        st.session_state["message"] = []
        st.rerun()

# 主界面
st.title("智联未来")
st.divider()

# 显示当前模型服务状态
current_service = st.session_state.get("model_service")
if current_service:
    service_type = "Ollama" if hasattr(current_service, 'client') else "Qianfan"
    st.caption(f"🌡️ Temperature: {st.session_state['temperature']} | 🔧 当前服务: {service_type}")

# 显示历史记录
if st.session_state["show_history"]:
    conversation_id = show_conversation_history(user_id=1, show_history=True)
    st.session_state["conversation_id"] = conversation_id
    if conversation_id:
        for message in st.session_state["message"]:
            content = message["content"]
            if message["role"] == "user" and "用户提问：" in content:
                content = content.split("用户提问：")[-1]
            st.chat_message(message["role"]).markdown(content)
elif st.session_state["conversation_id"]:
    conversation_id = st.session_state["conversation_id"]

# 聊天输入
prompt = st.chat_input("请输入你的问题：")
if prompt:
    if not st.session_state["model_service"]:
        st.warning("请先在侧边栏连接模型服务！")  # 添加明确的错误提示
    else:
        if st.session_state.get("conversation_id"):
            display_conversation(
                prompt=prompt,
                file_content=st.session_state.get('file_content', ''),
                model_service=st.session_state["model_service"],
                use_stream=use_stream,
                maxHistoryMessages=maxHistoryMessages,
                conversation_id=st.session_state["conversation_id"],
                user_id=1,
            )
        else:
            st.session_state["conversation_id"] = display_conversation(
                prompt=prompt,
                file_content=st.session_state.get('file_content', ''),
                model_service=st.session_state["model_service"],
                use_stream=use_stream,
                maxHistoryMessages=maxHistoryMessages,
            )
