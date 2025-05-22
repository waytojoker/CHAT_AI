import time
import ollama
import streamlit as st
import re
maxHistoryMessages = 10

# Ollama 客户端
client = ollama.Client(host="http://127.0.0.1:11434")

if "message" not in st.session_state:
    st.session_state['message'] = []

def preprocess_output(output):
    # 替换 $$...$$ 包裹的公式为 st.latex 可识别的形式
    # 例如：$$\boxed{8}$$ → \boxed{8}
    output = re.sub(r"\$\$(.*?)\$\$", r"$$\1$$", output)

    # 特别处理 \boxed{}，确保它在数学环境中显示
    if re.search(r"\\boxed\{.*?\}", output):
        output = re.sub(r"(\\boxed\{.*?\})", r"\n\1\n", output)

    return output

st.title("智联未来")
st.divider()  # 分割线
prompt = st.chat_input("请输入你的问题：")

# 1.角色 2.消息 [{"role": "user/assistant", "content": "你好"}]
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
            model='deepseek-r1:1.5b',
            #messages=[{"role": "user", "content": prompt}],
            messages=st.session_state["message"][-maxHistoryMessages:],
            stream=True  # 启用流式响应
        )

        # 创建一个空的占位符
        assistant_message_placeholder = st.empty()

        # 初始化一个空的回复内容
        assistant_message = ""

        # 模拟流式输出
        for chunk in response:
            if chunk.get("message"):
                # 追加新的内容
                assistant_message += chunk["message"]["content"]
                # 替换 <think> 和 </think>
                assistant_message = assistant_message.replace("<think>", "\n\n**思考：**\n")
                assistant_message = assistant_message.replace("</think>", "\n\n**回答：**\n")

                assistant_message = preprocess_output(assistant_message)  # 预处理输出

                # 逐步更新占位符内容
                assistant_message_placeholder.markdown(assistant_message)
                # 模拟生成速度
                time.sleep(0.05)  # 可以根据需要调整

        # 最终添加完整的回复到消息列表
        st.session_state["message"].append({"role": "assistant", "content": assistant_message})