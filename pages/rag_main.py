import streamlit as st
from modules.rag_module import show_rag_management, RAGSystem
from modules.enhanced_conversation_display import (
    display_rag_enhanced_conversation,
    show_rag_debug_info
)
from modules.file_processing import get_file_content
from modules.history_module import show_conversation_history
from modules.model_service import create_model_service, ModelService, QianfanModelService
import os

# 页面配置
#隐藏自动导航2
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)



# 初始化session state
def init_session_state():
    """初始化session state变量"""
    if "message" not in st.session_state:
        st.session_state["message"] = []

    if "current_conversation" not in st.session_state:
        st.session_state["current_conversation"] = 1

    if "show_history" not in st.session_state:
        st.session_state["show_history"] = False

    if "temperature" not in st.session_state:
        st.session_state["temperature"] = 0.7

    if "role_config" not in st.session_state:
        st.session_state["role_config"] = "你是一个有帮助的AI助手"

    if "scene_config" not in st.session_state:
        st.session_state["scene_config"] = "日常对话场景"

    if "task_config" not in st.session_state:
        st.session_state["task_config"] = "回答用户问题，提供有用的信息"

    if "use_rag" not in st.session_state:
        st.session_state["use_rag"] = False

    if "rag_system" not in st.session_state:
        st.session_state["rag_system"] = RAGSystem()

    if "show_rag_debug" not in st.session_state:
        st.session_state["show_rag_debug"] = False

    if "chunk_size" not in st.session_state:
        st.session_state["chunk_size"] = 500

    if "top_k" not in st.session_state:
        st.session_state["top_k"] = 3

    if "selected_model" not in st.session_state:
        st.session_state["selected_model"] = ""

    if "use_stream" not in st.session_state:
        st.session_state["use_stream"] = False

    if "maxHistoryMessages" not in st.session_state:
        st.session_state["maxHistoryMessages"] = 10

    if "model_service_type" not in st.session_state:
        st.session_state["model_service_type"] = "qianfan"

    if "model_service" not in st.session_state:
        st.session_state["model_service"] = None

    if "qianfan_authorization" not in st.session_state:
        st.session_state["qianfan_authorization"] = ""

    if "qianfan_model" not in st.session_state:
        st.session_state["qianfan_model"] = "ernie-4.5-turbo-vl-32k"


def init_model_service():
    """初始化模型服务"""
    try:
        service_type = st.session_state["model_service_type"]
        if service_type == "qianfan":
            # 初始化千帆服务
            authorization = st.session_state["qianfan_authorization"]
            model = st.session_state["qianfan_model"]

            if not authorization:
                st.error("请设置千帆授权令牌")
                return None

            st.session_state["model_service"] = create_model_service(
                "qianfan",
                authorization=authorization,
                model=model
            )



        return st.session_state["model_service"]

    except Exception as e:
        st.error(f"初始化模型服务失败: {e}")
        return None


def show_model_service_config():
    """显示模型服务配置"""
    st.subheader("🤖 模型服务配置")
    st.subheader("模型服务:qianfan")
    # 服务类型选择
    service_type = "qianfan"

    if service_type != st.session_state["model_service_type"]:
        st.session_state["model_service_type"] = service_type
        st.session_state["model_service"] = None  # 重置模型服务

    if service_type == "qianfan":
        # 千帆配置
        st.write("**百度千帆配置**")

        # 从环境变量或用户输入获取授权令牌
        env_auth = os.environ.get("QIANFAN_AUTHORIZATION", "")
        authorization = st.text_input(
            "授权令牌 (Authorization)",
            value=st.session_state.get("qianfan_authorization", "") or env_auth,
            type="password",
            help="请输入千帆API的授权令牌，格式如：Bearer bce-v3/xxx"
        )
        st.session_state["qianfan_authorization"] = authorization

        # 模型选择
        qianfan_models = [
            "ernie-4.5-turbo-vl-32k",
            "ernie-4.0-turbo-8k",
            "ernie-3.5-8k",
            "ernie-lite-8k"
        ]
        model = st.selectbox(
            "千帆模型",
            qianfan_models,
            index=qianfan_models.index(st.session_state.get("qianfan_model", "ernie-4.5-turbo-vl-32k"))
            if st.session_state.get("qianfan_model", "ernie-4.5-turbo-vl-32k") in qianfan_models else 0
        )
        st.session_state["qianfan_model"] = model

        # 显示网络配置提示
        st.info("💡 如果遇到网络连接问题，请检查：\n"
                "1. 网络代理设置\n"
                "2. 防火墙配置\n"
                "3. 授权令牌格式是否正确")

        # 测试连接
        if st.button("测试千帆连接"):
            if authorization:
                try:
                    with st.spinner("正在测试连接..."):
                        service = create_model_service("qianfan", authorization=authorization, model=model)
                        # 发送测试消息
                        test_messages = [{"role": "user", "content": "你好，请回复'连接成功'"}]
                        response = service.chat(test_messages)

                        if "choices" in response and len(response["choices"]) > 0:
                            st.success("✅ 千帆服务连接成功！")
                            st.session_state["model_service"] = service
                            st.write(f"测试回复: {response['choices'][0]['message']['content']}")
                        else:
                            st.error("❌ 千帆服务响应格式错误")

                except Exception as e:
                    st.error(f"❌ 千帆服务连接失败: {e}")
                    st.write("请检查网络连接和授权令牌")
            else:
                st.warning("请先输入授权令牌")

def test_rag_system():
    """测试RAG系统功能"""
    st.subheader("🧪 RAG系统测试")

    if 'rag_system' not in st.session_state:
        st.error("RAG系统未初始化")
        return

    rag_system = st.session_state.rag_system

    # 显示系统状态
    stats = rag_system.get_document_stats()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📚 文档数量", len(stats['files']))
    with col2:
        st.metric("📄 文档块数量", stats['total_chunks'])
    with col3:
        st.metric("🔑 关键词数量", stats['total_keywords'])

    if stats['total_chunks'] == 0:
        st.warning("⚠️ 请先上传并处理文档，然后再进行测试")
        return

    # 测试查询
    st.subheader("🔍 检索测试")
    test_query = st.text_input("输入测试查询", placeholder="例如：什么是人工智能？")

    if test_query:
        with st.spinner("正在搜索相关文档..."):
            results = rag_system.search_documents(test_query, top_k=5)

            if results:
                st.success(f"找到 {len(results)} 个相关文档块")

                for i, result in enumerate(results):
                    with st.expander(f"结果 {i + 1} - {result['filename']} (相关性: {result['relevance_score']:.2f})"):
                        st.write("**内容预览:**")
                        st.write(result['content'][:300] + "..." if len(result['content']) > 300 else result['content'])

                        st.write("**关键词:**")
                        st.write(", ".join(result['keywords'][:10]))
            else:
                st.warning("未找到相关文档")

    # 测试模型服务与RAG集成
    st.subheader("🤖 模型服务与RAG集成测试")

    if st.session_state["model_service"] and test_query:
        if st.button("测试RAG增强回答"):
            with st.spinner("正在生成RAG增强回答..."):
                try:
                    # 搜索相关文档
                    relevant_chunks = rag_system.search_documents(test_query, top_k=3)

                    if relevant_chunks:
                        # 生成RAG增强的提示词
                        enhanced_prompt = rag_system.generate_rag_prompt(test_query, relevant_chunks)

                        # 构建消息
                        messages = [{"role": "user", "content": enhanced_prompt}]

                        with st.spinner("正在思考..."):
                            # 使用模型服务生成回答
                            response = st.session_state["model_service"].chat(messages)

                        if "choices" in response and len(response["choices"]) > 0:
                            answer = response["choices"][0]["message"]["content"]
                            st.success("✅ RAG增强回答生成成功！")
                            st.write("**回答:**")
                            st.write(answer)

                            # 显示使用的文档片段
                            with st.expander("📚 参考文档片段"):
                                for i, chunk in enumerate(relevant_chunks):
                                    st.write(f"**片段 {i + 1}** ({chunk['filename']}):")
                                    st.write(chunk['content'][:200] + "..." if len(chunk['content']) > 200 else chunk[
                                        'content'])
                                    st.write("---")
                        else:
                            st.error("模型响应格式错误")
                    else:
                        st.warning("未找到相关文档，无法进行RAG增强")

                except Exception as e:
                    st.error(f"RAG增强回答生成失败: {e}")
                    import traceback
                    st.error(f"详细错误: {traceback.format_exc()}")

def show_system_status():
    """显示系统状态信息"""
    st.subheader("📊 系统状态")

    # 模型服务状态
    col1, col2 = st.columns(2)

    with col1:
        st.write("**模型服务状态:**")
        service_status = {
            "服务类型": st.session_state.get("model_service_type", "未设置"),
            "服务状态": "已连接" if st.session_state["model_service"] else "未连接",
        }

        if st.session_state["model_service_type"] == "qianfan":
            service_status["模型"] = st.session_state.get("qianfan_model", "未设置")
            service_status["授权状态"] = "已设置" if st.session_state.get("qianfan_authorization") else "未设置"

        st.json(service_status)

    # RAG系统状态
    with col2:
        if 'rag_system' in st.session_state:
            rag_stats = st.session_state.rag_system.get_document_stats()
            st.write("**RAG系统状态:**")
            st.json({
                "文档数量": len(rag_stats['files']),
                "文档块数量": rag_stats['total_chunks'],
                "关键词数量": rag_stats['total_keywords'],
                "RAG状态": "已启用" if st.session_state.get('use_rag', False) else "未启用"
            })

            st.write("**已处理文档:**")
            if rag_stats['files']:
                for filename, chunk_count in rag_stats['files'].items():
                    st.write(f"• {filename}: {chunk_count} 块")
            else:
                st.write("暂无文档")

    # 会话状态
    st.write("**当前会话状态:**")
    st.json({
        "消息数量": len(st.session_state.get("message", [])),
        "当前对话ID": st.session_state.get("current_conversation", 1),
        "温度设置": st.session_state.get("temperature", 0.7),
        "流式输出": st.session_state["use_stream"]
    })


def chat_with_model_service(prompt):
    """使用模型服务进行对话"""
    if not st.session_state["model_service"]:
        st.error("请先配置并连接模型服务")
        return None

    # RAG增强查询
    try:
        use_rag = st.session_state.get('use_rag', False)
        original_prompt = prompt
        relevant_chunks = []

        if use_rag and 'rag_system' in st.session_state:
            with st.spinner("正在搜索相关文档..."):
                rag_system = st.session_state.rag_system
                relevant_chunks = rag_system.search_documents(prompt, top_k=st.session_state.get('top_k', 3))

                if relevant_chunks:
                    prompt = rag_system.generate_rag_prompt(prompt, relevant_chunks)
                    st.info(f"🔍 找到 {len(relevant_chunks)} 个相关文档片段")

        # 处理文件内容

        # 构建系统提示词
        system_prompt = f"""角色设定：{st.session_state['role_config']}
场景设定：{st.session_state['scene_config']}
任务要求：{st.session_state['task_config']}

请根据以上设定进行对话。"""

        # 构建消息历史
        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史消息
        history_messages = st.session_state.get("message", [])[-st.session_state.get("maxHistoryMessages", 10):]
        messages.extend(history_messages)

        # 添加当前用户消息
        messages.append({"role": "user", "content": prompt})

        # 调用模型服务
        if st.session_state["model_service_type"] == "qianfan":
            # 千帆模型调用
            response = st.session_state["model_service"].chat(
                messages,
                temperature=st.session_state.get("temperature", 0.7),
                stream=st.session_state["use_stream"]
            )



    except Exception as e:
        st.error(f"模型调用失败: {e}")
        import traceback
        st.error(f"详细错误信息: {traceback.format_exc()}")
        return None


def main():
    """主应用函数"""
    init_session_state()

    # 标题
    st.title("🤖 RAG增强智能对话系统")
    st.caption("支持多种模型服务和私有文档检索的智能问答系统")

    # 侧边栏设置
    with st.sidebar:
        st.header("⚙️ 系统设置")
        # 返回按钮
        if st.button("← 返回主界面"):
                st.switch_page("chatting_test.py")  # 跳回主页面
        # 模型服务配置
        show_model_service_config()

        # 对话参数设置
        st.divider()
        st.subheader("💬 对话参数")
        st.session_state["temperature"] = st.slider(
            "温度 (创造性)",
            min_value=0.0,
            max_value=2.0,
            value=st.session_state["temperature"],
            step=0.1,
            help="较低值使回答更确定，较高值使回答更有创造性"
        )

        st.session_state["use_stream"] = False

        st.session_state["maxHistoryMessages"] = st.slider(
            "历史消息数量",
            min_value=2,
            max_value=50,
            value=st.session_state["maxHistoryMessages"],
            help="保留的历史消息数量"
        )

        # 角色设定
        st.divider()
        st.subheader("🎭 角色设定")
        st.session_state["role_config"] = st.text_area(
            "角色描述",
            value=st.session_state["role_config"],
            height=80,
            help="定义AI助手的角色和性格"
        )

        st.session_state["scene_config"] = st.text_area(
            "场景设定",
            value=st.session_state["scene_config"],
            height=68,
            help="描述对话的场景和环境"
        )

        st.session_state["task_config"] = st.text_area(
            "任务要求",
            value=st.session_state["task_config"],
            height=80,
            help="明确AI助手需要完成的任务"
        )



    # 主界面标签页
    tab1, tab2, tab3, tab4 = st.tabs(["💬 对话", "📚 文档管理", "🧪 系统测试", "📊 状态监控"])




    with tab1:

        # 对话界面
        st.header("智能对话")

        if not st.session_state["model_service"]:
            st.warning("⚠️ 请先在侧边栏配置并连接模型服务")
            return

        rag_system = st.session_state.rag_system
        stats = rag_system.get_document_stats()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📚 文档数量", len(stats['files']))
        with col2:
            st.metric("📄 文档块数量", stats['total_chunks'])
        with col3:
            st.metric("🔑 关键词数量", stats['total_keywords'])
        # 显示对话历史
        # for message in st.session_state.get("message", []):
        #     with st.chat_message(message["role"]):
        #         st.markdown(message["content"])

        if st.button("🗑️ 清空对话", type="secondary"):
            st.session_state["message"] = []
            st.rerun()

        test_query = st.chat_input("输入你的问题...")
        if test_query:
            try:
                # 搜索相关文档
                relevant_chunks = rag_system.search_documents(test_query, top_k=3)

                if relevant_chunks:
                    # 生成RAG增强的提示词
                    enhanced_prompt = rag_system.generate_rag_prompt(test_query, relevant_chunks)

                    # 构建消息
                    # 添加用户消息（仅显示提问部分）
                    user_message = {"role": "user", "content": enhanced_prompt,"original_question": test_query}
                    st.session_state["message"].append(user_message)

                    #显示先前消息
                    for message in st.session_state["message"]:
                        if message["role"] == "user":
                            content = message["original_question"]
                            content = content.split("用户提问：")[-1]
                        else:
                            content = message["content"]
                        st.chat_message(message["role"]).markdown(content)

                    # 使用模型服务生成回答
                    response = st.session_state["model_service"].chat(st.session_state["message"])

                    if "choices" in response and len(response["choices"]) > 0:
                        answer = response["choices"][0]["message"]["content"]
                        st.success("✅ RAG增强回答生成成功！")
                        st.write("**回答:**")
                        st.write(answer)

                        assistant_message = {"role": "assistant", "content": answer}
                        st.session_state["message"].append(assistant_message)

                        # 显示使用的文档片段
                        with st.expander("📚 参考文档片段"):
                            for i, chunk in enumerate(relevant_chunks):
                                st.write(f"**片段 {i + 1}** ({chunk['filename']}):")
                                st.write(chunk['content'][:200] + "..." if len(chunk['content']) > 200 else chunk[
                                    'content'])
                                st.write("---")
                    else:
                        st.error("模型响应格式错误")
                else:
                    st.warning("未找到相关文档，无法进行RAG增强")

            except Exception as e:
                st.error(f"RAG增强回答生成失败: {e}")
                import traceback
                st.error(f"详细错误: {traceback.format_exc()}")

    with tab2:



        # 文档管理界面
        st.header("私有文档管理")
        show_rag_management()

        # RAG参数调整
        st.subheader("🔧 RAG参数调整")
        col1, col2 = st.columns(2)

        with col1:
            new_chunk_size = st.slider(
                "文档分块大小",
                min_value=200,
                max_value=1000,
                value=st.session_state.get('chunk_size', 500),
                step=50,
                help="调整后需要重新处理文档"
            )

        with col2:
            new_top_k = st.slider(
                "检索文档数量",
                min_value=1,
                max_value=10,
                value=st.session_state.get('top_k', 3),
                help="每次查询返回的相关文档块数量"
            )

        # 检查参数是否改变
        if (new_chunk_size != st.session_state.get('chunk_size', 500) or
                new_top_k != st.session_state.get('top_k', 3)):

            st.session_state['chunk_size'] = new_chunk_size
            st.session_state['top_k'] = new_top_k

            # 更新RAG系统参数
            if 'rag_system' in st.session_state:
                st.session_state.rag_system.processor.chunk_size = new_chunk_size
                st.info("参数已更新，建议重新处理文档以获得最佳效果")

    with tab3:

        # 系统测试界面
        st.header("系统功能测试")
        test_rag_system()

        # RAG调试信息
        if st.session_state.get("show_rag_debug", False):
            show_rag_debug_info()

    with tab4:

        # 状态监控界面
        st.header("系统状态监控")
        show_system_status()

        # 性能监控
        st.subheader("📈 性能监控")

        if st.button("🔄 刷新状态"):
            st.rerun()

        # 系统健康检查
        st.subheader("🏥 系统健康检查")

        col1, col2, col3 = st.columns(3)

        with col1:
            # 模型服务检查
            if st.session_state["model_service"]:
                st.success("✅ 模型服务正常")
            else:
                st.error("❌ 模型服务未连接")

        with col2:
            # RAG系统测试
            if 'rag_system' in st.session_state:
                stats = st.session_state.rag_system.get_document_stats()
                if stats['total_chunks'] > 0:
                    st.success("✅ RAG系统正常")
                else:
                    st.warning("⚠️ RAG系统无文档")
            else:
                st.error("❌ RAG系统未初始化")

        with col3:
            # 会话状态测试
            if st.session_state.get("message"):
                st.success("✅ 会话状态正常")
            else:
                st.info("ℹ️ 暂无会话历史")


if __name__ == "__main__":
    main()
