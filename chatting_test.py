import time
import ollama
import streamlit as st
import re
maxHistoryMessages = 10

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

def preprocess_output(output):
    # 替换 $$...$$ 包裹的公式为 st.latex 可识别的形式
    # 例如：$$\boxed{8}$$ → \boxed{8}
    output = output.replace("<think>", "\n\n**思考：**\n")
    output = output.replace("</think>", "\n\n**回答：**\n")
    output = re.sub(r"\$\$(.*?)\$\$", r"$$\1$$", output)
    output = re.sub(r"\\boxed\{(.*?)\}", r"\1", output)

    return output
def get_system_prompt():
    """构建系统提示词"""
    return f"""角色设定：{st.session_state['role_config']}

场景设定：{st.session_state['scene_config']}

任务要求：{st.session_state['task_config']}

请根据以上设定进行对话。"""

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置设置")

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

st.title("智联未来")
st.divider()  # 分割线

# 显示当前配置状态
col1, col2 = st.columns([3, 1])
with col2:
    st.caption(f"🌡️ Temperature: {st.session_state['temperature']}")

prompt = st.chat_input("请输入你的问题：")
# 是否使用流式的按钮
use_stream = st.checkbox("使用流式响应", value=True)
# 模型选择下拉框
models = ["deepseek-r1:7b", "deepseek-r1:1.5b"]  # 可以根据需要添加更多模型
selected_model = st.selectbox("选择模型", models)


if prompt:
    # 添加用户消息
    st.session_state["message"].append({"role": "user", "content": prompt})

    # 显示用户消息
    for message in st.session_state["message"]:
        st.chat_message(message["role"]).markdown(message["content"])

    # 获取 Ollama 的回复
    with st.spinner("正在思考..."):
        # 获取 Ollama 的回复
        response = client.chat(
            model='deepseek-r1:7b',
            #messages=[{"role": "user", "content": prompt}],
            messages=st.session_state["message"][-maxHistoryMessages:],
            stream=use_stream,  # 根据按钮状态启用流式响应
            options = {
                "temperature": st.session_state['temperature']
            }
        )

        if use_stream:
            # 创建一个空的占位符
            assistant_message_placeholder = st.empty()

            # 初始化一个空的回复内容
            assistant_message = ""

            # 模拟流式输出
            for chunk in response:
                if chunk.get("message"):
                    # 追加新的内容
                    assistant_message += chunk["message"]["content"]
                    # 预处理输出
                    assistant_message = preprocess_output(assistant_message)  
                    # 逐步更新占位符内容
                    assistant_message_placeholder.markdown(assistant_message)
                    # 模拟生成速度
                    time.sleep(0.05)  # 可以根据需要调整

            # 最终添加完整的回复到消息列表
            st.session_state["message"].append({"role": "assistant", "content": assistant_message})
        else:

            response['message']['content'] = preprocess_output(response['message']['content'])  # 预处理输出

            # 添加ollama的回复
            st.session_state["message"].append({"role": "assistant", "content": response['message']['content']})
            # 显示ollama的回复
            st.chat_message("assistant").markdown(response['message']['content'])