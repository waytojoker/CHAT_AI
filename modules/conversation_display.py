import time
import re
import streamlit as st
import requests
from modules.tokens.API_TOKEN import get_access_token
# 导入MCP工具调用相关模块
from modules.mcp_client import run_async_function
local_models = ["deepseek-r1:7b", "deepseek-r1:1.5b"]
import json

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
    base_prompt = f"""角色设定：{st.session_state['role_config']}

场景设定：{st.session_state['scene_config']}

任务要求：{st.session_state['task_config']}

请根据以上设定进行对话。"""

    # 如果启用了MCP且是自主模式，添加工具信息
    if (st.session_state.get("enable_mcp", False) and 
        st.session_state.get("mcp_tool_caller") and 
        st.session_state.get("auto_tool_mode", True)):
        tools_description = st.session_state["mcp_tool_caller"].get_tools_description_for_ai()
        if tools_description:
            base_prompt += "\n\n" + tools_description

    return base_prompt

def handle_ai_response_with_tools(response_text, client, selected_model, use_stream, messages):
    """处理AI回复中的工具调用，如果包含工具调用则执行并重新生成回复"""
    # 只在自主模式下处理AI回复中的工具调用
    if (not st.session_state.get("enable_mcp", False) or 
        not st.session_state.get("mcp_tool_caller") or
        not st.session_state.get("auto_tool_mode", True)):
        return response_text, []
    
    # 检查回复中是否包含工具调用
    mcp_results = run_async_function(
        st.session_state["mcp_tool_caller"].parse_and_execute_tools(response_text)
    )
    
    if not mcp_results:
        return response_text, []
    
    # 如果有工具调用，将结果添加到对话历史中并重新生成回复
    formatted_results = st.session_state["mcp_tool_caller"].format_tool_result(mcp_results)
    
    # 添加工具结果到消息历史
    tool_result_message = {
        "role": "system", 
        "content": f"工具执行结果：\n{formatted_results}\n\n请基于这些工具结果重新生成回答，不要再次调用工具。"
    }
    
    # 重新调用模型
    new_messages = messages + [{"role": "assistant", "content": response_text}, tool_result_message]
    
    try:
        if selected_model in local_models:
            new_response = client.chat(
                model=selected_model,
                messages=new_messages,
                stream=False,  # 这里不使用流式，避免复杂性
                options={"temperature": st.session_state['temperature']}
            )
            final_response = new_response['message']['content']
        else:
            # 处理API模型的情况
            final_response = "基于工具执行结果，我现在可以为您提供更准确的信息。"
        
        return final_response, mcp_results
        
    except Exception as e:
        st.error(f"重新生成回复时出错: {str(e)}")
        return response_text, mcp_results

def display_conversation(prompt, file_content, client, selected_model, use_stream, maxHistoryMessages, conversation_id=1, user_id=1):
    original_prompt = prompt
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

    # 检查手动工具调用模式
    manual_mcp_results = []
    if (st.session_state.get("enable_mcp", False) and 
        st.session_state.get("mcp_tool_caller") and 
        not st.session_state.get("auto_tool_mode", True)):
        try:
            # 先解析工具调用信息
            tool_calls = st.session_state["mcp_tool_caller"]._parse_tool_calls_from_text(prompt)
            
            # 如果有工具调用，先显示调用的工具信息
            if tool_calls:
                with st.expander("🔍 检测到的工具调用", expanded=True):
                    tool_info = []
                    for i, tool_call in enumerate(tool_calls, 1):
                        tool_info.append(f"**工具 {i}:**\n")
                        tool_info.append(f"- 服务器: `{tool_call['server']}`\n")
                        tool_info.append(f"- 工具名: `{tool_call['tool']}`\n")
                        tool_info.append(f"- 参数: `{json.dumps(tool_call['arguments'], ensure_ascii=False)}`\n")
                    st.markdown("".join(tool_info))
            
            # 执行工具调用
            manual_mcp_results = run_async_function(
                st.session_state["mcp_tool_caller"].parse_and_execute_tools(prompt)
            )
            
            # 如果有手动工具调用结果，显示
            if manual_mcp_results:
                with st.expander("🛠️ 手动工具执行结果", expanded=True):
                    formatted_results = st.session_state["mcp_tool_caller"].format_tool_result(manual_mcp_results)
                    st.markdown(formatted_results)
                
                # 将工具结果添加到prompt中，供AI参考
                tool_results_text = f"\n\n工具执行结果：\n{formatted_results}"
                prompt += tool_results_text
                user_message["content"] = original_prompt  # 保持原始用户消息不变
                
        except Exception as e:
            st.error(f"手动工具调用失败: {str(e)}")

    with st.spinner("正在思考..."):
        system_message = {"role": "system", "content": get_system_prompt()}
        user_messages = st.session_state["message"][-maxHistoryMessages:]
        messages = [system_message] + user_messages

        # 获取API模型回答
        if selected_model not in local_models:
            payload = json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    },
                ],
                "temperature": st.session_state['temperature'],
                "top_p": 0.7,
                "penalty_score": 1
            })
            headers = {'Content-Type': 'application/json'}
            if selected_model == "ernie-speed-128k(无流式API)":
                url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k?access_token=" + get_access_token()
                response = requests.request("POST", url, headers=headers, data=payload).json()
                response = {"message": {"content": response['result']}}
        # 获取 本地(Ollama) 的回复
        else:
            response = client.chat(
                model=selected_model,
                messages=messages,
                stream=use_stream,
                options={"temperature": st.session_state['temperature']}
            )
    with st.spinner("正在回答..."):
        if use_stream and selected_model != "ernie-speed-128k(无流式API)":
            assistant_message = ""
            assistant_message_placeholder = st.empty()
            for chunk in response:
                if chunk.get("message"):
                    assistant_message += chunk["message"]["content"]
                    assistant_message = preprocess_output(assistant_message)
                    assistant_message_placeholder.markdown(assistant_message)
                    time.sleep(0.05)
            
            # 处理可能的工具调用
            final_response, mcp_results = handle_ai_response_with_tools(
                assistant_message, client, selected_model, use_stream, messages
            )
            
            # 如果有工具调用，显示工具执行结果
            if mcp_results:
                with st.expander("🛠️ AI自主调用的工具执行结果", expanded=True):
                    formatted_results = st.session_state["mcp_tool_caller"].format_tool_result(mcp_results)
                    st.markdown(formatted_results)
                
                # 更新显示的回复
                assistant_message_placeholder.markdown(preprocess_output(final_response))
                assistant_message = final_response
            
            assistant_message = {"role": "assistant", "content": assistant_message}
            st.session_state["message"].append(assistant_message)
        else:
            response['message']['content'] = preprocess_output(response['message']['content'])
            
            # 处理可能的工具调用
            final_response, mcp_results = handle_ai_response_with_tools(
                response['message']['content'], client, selected_model, use_stream, messages
            )
            
            # 如果有工具调用，显示工具执行结果
            if mcp_results:
                with st.expander("🛠️ AI自主调用的工具执行结果", expanded=True):
                    formatted_results = st.session_state["mcp_tool_caller"].format_tool_result(mcp_results)
                    st.markdown(formatted_results)
                
                response['message']['content'] = final_response
            
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
    try:
        response = requests.post(f"http://127.0.0.1:5000/save_conversation", json=data)
        if response.status_code == 200:
            return conversation_id
        else:
            st.error("保存对话失败。")
            return None
    except Exception as e:
        st.error(f"保存对话时出错: {e}")
        return None

