import time
import ollama
import streamlit as st
import requests
import json
import re

#ollama 客户端
client = ollama.Client(host="http://127.0.0.1:11434")

if "message" not in st.session_state:
    st.session_state['message'] = []

def preprocess_output(output):
    output = re.sub(r"\$\$(.*?)\$\$", r"$$\1$$", output)
    if re.search(r"\\boxed\{.*?\}", output):
        output = re.sub(r"(\\boxed\{.*?\})", r"\n\1\n", output)
    return output

st.title("智联未来")
st.divider()#分割线
prompt=st.chat_input("请输入你的问题：")

#1.角色 2.消息 [{"role": "user/assistant", "content": "你好"}]
if prompt:
    #添加用户消息
    st.session_state["message"].append({"role": "user", "content": prompt})

    #显示用户消息
    for message in st.session_state["message"]:
        st.chat_message(message["role"]).markdown(message["content"])

    #获取ollama的回复
    with st.spinner("正在思考..."):
        #获取ollama的回复
        response = client.chat(
            model='deepseek-r1:1.5b',
            messages=[{"role": "user", "content": prompt}]
        )
        response['message']['content'] = response['message']['content'].replace("<think>", "\n\n**思考：**\n")
        response['message']['content'] = response['message']['content'].replace("</think>", "\n\n**回答：**\n")
        response['message']['content'] = preprocess_output(response['message']['content'])
        #添加ollama的回复
        st.session_state["message"].append({"role": "assistant", "content": response['message']['content']})
        #显示ollama的回复
        st.chat_message("assistant").markdown(response['message']['content'])

