import time
import re
import streamlit as st
import requests

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

def display_conversation(prompt, file_content, client, selected_model, use_stream, maxHistoryMessages, conversation_id=1, user_id=1):
    """
    封装对话展示逻辑。
    """
    if file_content is not None:
        prompt = file_content + prompt
    full_prompt = f"{file_content}\n\n用户提问：{prompt}"

    # 添加用户消息（仅显示提问部分）
    user_message = {"role": "user", "content": prompt}
    st.session_state["message"].append(user_message)

    # 显示先前消息
    for message in st.session_state["message"]:
        content = message["content"]
        if message["role"] == "user" and "用户提问：" in content:
            content = content.split("用户提问：")[-1]
        st.chat_message(message["role"]).markdown(content)

    # 获取 Ollama 的回复
    with st.spinner("正在思考..."):
        system_message = {"role": "system", "content": get_system_prompt()}
        user_messages = st.session_state["message"][-maxHistoryMessages:]
        messages = [system_message] + user_messages

        response = client.chat(
            model=selected_model,
            messages=messages,
            stream=use_stream,
            options={"temperature": st.session_state['temperature']}
        )

        if use_stream:
            assistant_message = ""
            assistant_message_placeholder = st.empty()
            for chunk in response:
                if chunk.get("message"):
                    assistant_message += chunk["message"]["content"]
                    assistant_message = preprocess_output(assistant_message)
                    assistant_message_placeholder.markdown(assistant_message)
                    time.sleep(0.05)
            assistant_message = {"role": "assistant", "content": assistant_message}
            st.session_state["message"].append(assistant_message)
        else:
            response['message']['content'] = preprocess_output(response['message']['content'])
            assistant_message = {"role": "assistant", "content": response['message']['content']}
            st.session_state["message"].append(assistant_message)
            st.chat_message("assistant").markdown(response['message']['content'])

    # 调用 Flask 后端接口保存对话
    save_conversation([user_message, assistant_message],  user_id, conversation_id)
    return conversation_id

def save_conversation(messages,  user_id=1, conversation_id=1):

    # 构造请求数据
    data = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "messages": messages
    }

    # 调用 Flask 后端接口保存对话
    response = requests.post(f"http://127.0.0.1:5000/save_conversation", json=data)
    if response.status_code == 200:
        return conversation_id
    else:
        st.write("保存对话失败。")