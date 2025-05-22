import ollama
import streamlit

client = ollama.Client(host="http://127.0.0.1:11434")

# # 列出模型
# print(client.list())
# # 查看模型详情
# print(client.show('deepseek-r1:1.5b'))
# #  查看进程
# print(client.ps())

while True:
    prompt = input("请输入问题：")
    response = client.chat(
        model='deepseek-r1:1.5b',
        messages=[{"role": "user", "content": prompt}]
    )
    print(response['message']['content'])


