import time
import re
import streamlit as st
import requests
from modules.file_processing import read_file
from modules.rag_module import enhance_query_with_rag


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


def display_conversation(prompt, file_content, client, selected_model, use_stream, maxHistoryMessages,
                         conversation_id=1, user_id=1, use_rag=False):
    """
    封装对话展示逻辑，集成RAG功能。
    """
    original_prompt = prompt

    # RAG增强查询
    if use_rag:
        with st.spinner("正在搜索相关文档..."):
            enhanced_prompt, relevant_chunks = enhance_query_with_rag(prompt, use_rag)

            # 显示搜索到的相关文档
            if relevant_chunks:
                st.info(f"🔍 找到 {len(relevant_chunks)} 个相关文档片段")

                # 在侧边栏显示相关文档详情
                with st.sidebar:
                    st.subheader("📄 相关文档片段")
                    for i, chunk in enumerate(relevant_chunks):
                        with st.expander(
                                f"片段 {i + 1} - {chunk['filename']} (相关性: {chunk['relevance_score']:.2f})"):
                            st.write(
                                chunk['content'][:300] + "..." if len(chunk['content']) > 300 else chunk['content'])

                prompt = enhanced_prompt
            else:
                st.warning("🔍 未找到相关文档片段，使用原始查询")

    # 处理文件内容
    if file_content is not None:
        prompt = file_content + prompt

    full_prompt = f"{file_content}\n\n用户提问：{original_prompt}" if file_content else f"用户提问：{original_prompt}"

    # 添加用户消息（显示原始提问）
    user_message = {"role": "user", "content": original_prompt}
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

        # 构建消息列表，如果使用RAG，则用增强后的prompt替换最后一条用户消息
        messages = [system_message] + user_messages[:-1]
        if use_rag and relevant_chunks:
            # 使用增强后的prompt
            messages.append({"role": "user", "content": prompt})
        else:
            messages.append(user_messages[-1])

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
    save_conversation([user_message, assistant_message], user_id, conversation_id)
    return conversation_id


def save_conversation(messages, user_id=1, conversation_id=1):
    """保存对话到后端"""
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


def show_rag_settings():
    """显示RAG设置选项"""
    st.subheader("🔧 rag 设置")

    # RAG开关
    use_rag = st.checkbox(
        "启用RAG（检索增强生成）",
        value=st.session_state.get('use_rag', False),
        help="启用后将在回答问题时搜索相关文档内容"
    )
    st.session_state['use_rag'] = use_rag

    if use_rag:
        # RAG参数设置
        st.subheader("📋 rag 参数")

        col1, col2 = st.columns(2)

        with col1:
            chunk_size = st.slider(
                "文档块大小",
                min_value=200,
                max_value=1000,
                value=st.session_state.get('chunk_size', 500),
                help="每个文档块的字符数"
            )
            st.session_state['chunk_size'] = chunk_size

        with col2:
            top_k = st.slider(
                "检索文档数量",
                min_value=1,
                max_value=10,
                value=st.session_state.get('top_k', 3),
                help="每次查询返回的相关文档块数量"
            )
            st.session_state['top_k'] = top_k

        # 显示RAG状态
        if 'rag_system' in st.session_state:
            stats = st.session_state.rag_system.get_document_stats()
            st.info(f"📊 RAG状态: {stats['total_chunks']} 个文档块，{len(stats['files'])} 个文档")
        else:
            st.warning("⚠️ RAG系统未初始化")

    return use_rag


def display_rag_enhanced_conversation(prompt, file_content, client, selected_model, use_stream, maxHistoryMessages,
                                      conversation_id=1, user_id=1):
    """
    RAG增强的对话显示函数
    """
    use_rag = st.session_state.get('use_rag', False)

    return display_conversation(
        prompt=prompt,
        file_content=file_content,
        client=client,
        selected_model=selected_model,
        use_stream=use_stream,
        maxHistoryMessages=maxHistoryMessages,
        conversation_id=conversation_id,
        user_id=user_id,
        use_rag=use_rag
    )


def show_rag_debug_info():
    """显示RAG调试信息"""
    if st.session_state.get('show_rag_debug', False) and 'rag_system' in st.session_state:
        st.subheader("🔍 rag 调试信息")

        rag_system = st.session_state.rag_system
        stats = rag_system.get_document_stats()

        # 显示索引统计
        st.json({
            "文档统计": stats,
            "关键词示例": list(rag_system.index.keyword_index.keys())[:10] if rag_system.index.keyword_index else []
        })

        # 测试查询
        test_query = st.text_input("测试查询", placeholder="输入测试查询...")
        if test_query:
            results = rag_system.search_documents(test_query, top_k=5)
            st.write(f"找到 {len(results)} 个相关文档块:")
            for i, result in enumerate(results):
                st.write(f"**结果 {i + 1}** (相关性: {result['relevance_score']:.2f})")
                st.write(f"来源: {result['filename']}")
                st.write(f"内容: {result['content'][:200]}...")
                st.write("---")
