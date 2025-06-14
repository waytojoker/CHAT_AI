import streamlit as st
import requests
def show_conversation_history(user_id=1, show_history=True):
    """
    显示当前用户的所有对话历史。
    每个对话是一个可展开的组件，点击后显示该对话的所有消息。
    """
    if not show_history:
        return None

    # 调用 Flask 后端接口获取对话历史
    response = requests.get(f"http://127.0.0.1:5000/get_conversations", json={"user_id": user_id})
    if response.status_code != 200:
        st.write("暂无历史记录。")
        return None

    conversations = response.json().get("conversations", [])
    if not conversations:
        st.write("暂无历史记录。")
        return None

    for conversation in conversations:
        conversation_id = conversation["conversation_id"]
        timestamp = conversation["timestamp"]
        messages = conversation["content"]

        # 创建一个可展开的组件
        with st.expander(f"对话 {conversation_id} - {timestamp}", expanded=False):
            # 在展开组件的标题部分添加“跳转到对话”按钮
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"跳转到对话 {conversation_id}", key=f"switch_{conversation_id}"):
                    st.session_state["current_conversation"] = conversation_id
                    st.session_state["message"] = messages  # 将当前对话的消息加载到聊天区域
                    st.session_state["show_history"] = False  # 关闭历史记录显示
                    return conversation_id;
            with col2:
                if st.button(f"删除对话 {conversation_id}", key=f"delete_{conversation_id}"):
                    # 调用 Flask 后端接口删除对话历史
                    delete_response = requests.post(f"http://127.0.0.1:5000/delete_conversation_history", json={"user_id": user_id, "conversation_id": conversation_id})
                    if delete_response.status_code == 200:
                        st.write(f"对话 {conversation_id} 已删除。")
                    else:
                        st.write(f"删除对话 {conversation_id} 失败。")

