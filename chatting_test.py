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
    output = output.replace("<think>", "\n\n**思考：**\n")
    output = output.replace("</think>", "\n\n**回答：**\n")
    output = re.sub(r"\$\$(.*?)\$\$", r"$$\1$$", output)
    output = re.sub(r"\\boxed\{(.*?)\}", r"\1", output)

    return output

st.title("智联未来")
st.divider()  # 分割线

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
            stream=use_stream  # 根据按钮状态启用流式响应
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