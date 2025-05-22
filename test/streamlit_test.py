import time
import streamlit as st
import requests
import json

API_KEY = "E3YJqrvvOwJdr0WKZje1DYne"
SECRET_KEY = "3Bps5tv2SRIpuJHJFYkoNU9HKLPVnoHZ"

# 获取百度文心一言的 access_token
def get_access_token(api_key, secret_key):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k?access_token=" + get_access_token(API_KEY,SECRET_KEY)


# 设置页面标题和布局
st.set_page_config(page_title="智联未来")
st.title("智联未来")

with st.spinner("正在获取答案..."):
    st.write("你好")

# 用户输入问题
user_input = st.chat_input("请输入你的问题")

# with  st.spinner("正在获取答案..."):
#     time.sleep(5)
#     st.write("111")

#消息容器
#角色支持：user,assistant,ai,human
st.chat_message('user').markdown(user_input)
st.chat_message('assistant').markdown("正在获取答案...")



