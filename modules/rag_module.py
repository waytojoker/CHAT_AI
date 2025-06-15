import json
import os
import re
import jieba
from collections import defaultdict, Counter
import hashlib
from datetime import datetime
import streamlit as st
from file_processing import read_file


class DocumentProcessor:
    """文档处理类：负责文档分块、关键词提取和索引构建"""

    def __init__(self, chunk_size=500, overlap=50):
        self.chunk_size = chunk_size  # 文档块大小
        self.overlap = overlap  # 重叠字符数
        self.stop_words = self._load_stop_words()

    def _load_stop_words(self):
        """加载停用词列表"""
        # 常见中文停用词
        stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '一', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '什么', '如果', '可以', '但是', '因为', '所以',
            '这个', '那个', '他们', '我们', '它们', '这些', '那些', '已经', '还是', '只是', '应该', '可能', '或者',
            '虽然', '然后', '不过', '而且', '因此', '如何', '为什么', '哪里', '什么时候', '怎么样', '比如', '例如',
            '首先', '其次', '最后', '另外', '此外', '总之', '总的来说'
        }
        return stop_words

    def split_document(self, content, filename):
        """将文档分割成块"""
        if not content or len(content.strip()) == 0:
            return []

        chunks = []
        start = 0
        chunk_id = 0

        while start < len(content):
            end = min(start + self.chunk_size, len(content))

            # 尝试在句号、感叹号、问号处断句
            if end < len(content):
                for i in range(end, max(start + self.chunk_size // 2, end - 100), -1):
                    if content[i] in '。！？\n':
                        end = i + 1
                        break

            chunk_content = content[start:end].strip()
            if chunk_content:
                chunk = {
                    'chunk_id': f"{filename}_{chunk_id}",
                    'filename': filename,
                    'content': chunk_content,
                    'start_pos': start,
                    'end_pos': end,
                    'keywords': self.extract_keywords(chunk_content)
                }
                chunks.append(chunk)
                chunk_id += 1

            # 计算下一个块的起始位置（考虑重叠）
            start = max(start + 1, end - self.overlap)

        return chunks

    def extract_keywords(self, text):
        """从文本中提取关键词"""
        # 使用jieba分词
        words = jieba.cut(text)

        # 过滤停用词和短词
        keywords = []
        for word in words:
            word = word.strip()
            if (len(word) >= 2 and
                    word not in self.stop_words and
                    not word.isspace() and
                    not word.isdigit() and
                    re.match(r'^[a-zA-Z\u4e00-\u9fa5]+$', word)):
                keywords.append(word)

        # 统计词频并返回前20个关键词
        word_count = Counter(keywords)
        return [word for word, count in word_count.most_common(20)]


class DocumentIndex:
    """文档索引类：负责构建和维护关键词索引"""

    def __init__(self, index_file="document_index.json"):
        self.index_file = index_file
        self.keyword_index = defaultdict(list)  # 关键词 -> 文档块列表
        self.document_chunks = {}  # 文档块ID -> 文档块内容
        self.load_index()

    def add_document_chunks(self, chunks):
        """添加文档块到索引"""
        for chunk in chunks:
            chunk_id = chunk['chunk_id']
            self.document_chunks[chunk_id] = chunk

            # 为每个关键词建立索引
            for keyword in chunk['keywords']:
                if chunk_id not in [item['chunk_id'] for item in self.keyword_index[keyword]]:
                    self.keyword_index[keyword].append({
                        'chunk_id': chunk_id,
                        'filename': chunk['filename'],
                        'relevance': chunk['keywords'].count(keyword)  # 关键词在该块中的频次
                    })

    def search_by_keywords(self, query, top_k=5):
        """基于关键词搜索相关文档块"""
        # 提取查询关键词
        processor = DocumentProcessor()
        query_keywords = processor.extract_keywords(query)

        if not query_keywords:
            return []

        # 计算每个文档块的相关性得分
        chunk_scores = defaultdict(float)

        for keyword in query_keywords:
            if keyword in self.keyword_index:
                for item in self.keyword_index[keyword]:
                    chunk_id = item['chunk_id']
                    # 简单的TF-IDF近似：词频 * 逆文档频率
                    tf = item['relevance']
                    idf = len(self.document_chunks) / len(self.keyword_index[keyword])
                    chunk_scores[chunk_id] += tf * idf

        # 按得分排序并返回top_k个结果
        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for chunk_id, score in sorted_chunks[:top_k]:
            if chunk_id in self.document_chunks:
                chunk = self.document_chunks[chunk_id].copy()
                chunk['relevance_score'] = score
                results.append(chunk)

        return results

    def save_index(self):
        """保存索引到文件"""
        index_data = {
            'keyword_index': dict(self.keyword_index),
            'document_chunks': self.document_chunks,
            'last_updated': datetime.now().isoformat()
        }

        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    def load_index(self):
        """从文件加载索引"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    self.keyword_index = defaultdict(list, index_data.get('keyword_index', {}))
                    self.document_chunks = index_data.get('document_chunks', {})
            except Exception as e:
                print(f"加载索引失败: {e}")
                self.keyword_index = defaultdict(list)
                self.document_chunks = {}

    def delete_document(self, filename):
        """删除指定文件的所有文档块"""
        # 找到要删除的chunk_ids
        chunks_to_delete = [chunk_id for chunk_id, chunk in self.document_chunks.items()
                            if chunk['filename'] == filename]

        # 从document_chunks中删除
        for chunk_id in chunks_to_delete:
            del self.document_chunks[chunk_id]

        # 从keyword_index中删除
        for keyword in list(self.keyword_index.keys()):
            self.keyword_index[keyword] = [item for item in self.keyword_index[keyword]
                                           if item['chunk_id'] not in chunks_to_delete]
            # 如果某个关键词没有对应的文档块了，删除该关键词
            if not self.keyword_index[keyword]:
                del self.keyword_index[keyword]


class RAGSystem:
    """RAG系统主类：整合文档处理、索引和检索功能"""

    def __init__(self):
        self.processor = DocumentProcessor()
        self.index = DocumentIndex()

    def add_document(self, file_obj, filename=None):
        """添加文档到RAG系统"""
        if filename is None:
            filename = getattr(file_obj, 'name', 'unknown_file')

        # 读取文件内容
        content = read_file(file_obj)
        if not content:
            return False, "无法读取文件内容"

        # 删除同名文件的旧索引（如果存在）
        self.index.delete_document(filename)

        # 分割文档
        chunks = self.processor.split_document(content, filename)
        if not chunks:
            return False, "文档分割失败"

        # 添加到索引
        self.index.add_document_chunks(chunks)

        # 保存索引
        self.index.save_index()

        return True, f"成功处理文档 {filename}，分割成 {len(chunks)} 个文档块"

    def search_documents(self, query, top_k=3):
        """搜索相关文档"""
        return self.index.search_by_keywords(query, top_k)

    def generate_rag_prompt(self, query, context_chunks):
        """生成包含上下文的提示词"""
        if not context_chunks:
            return query

        context_text = "\n\n".join([
            f"文档片段 {i + 1} (来源: {chunk['filename']}):\n{chunk['content']}"
            for i, chunk in enumerate(context_chunks)
        ])

        rag_prompt = f"""请基于以下文档内容回答问题。

相关文档内容：
{context_text}

用户问题：{query}

请根据上述文档内容回答问题。如果文档中没有相关信息，请明确说明。"""

        return rag_prompt

    def get_document_stats(self):
        """获取文档统计信息"""
        total_chunks = len(self.index.document_chunks)
        total_keywords = len(self.index.keyword_index)

        # 按文件统计
        file_stats = defaultdict(int)
        for chunk in self.index.document_chunks.values():
            file_stats[chunk['filename']] += 1

        return {
            'total_chunks': total_chunks,
            'total_keywords': total_keywords,
            'files': dict(file_stats)
        }

    def delete_document(self, filename):
        """删除指定文档"""
        self.index.delete_document(filename)
        self.index.save_index()
        return f"已删除文档: {filename}"


# Streamlit界面组件
def show_rag_management():
    """显示RAG文档管理界面"""
    st.subheader("📚 私有文档管理")

    # 初始化RAG系统
    if 'rag_system' not in st.session_state:
        st.session_state.rag_system = RAGSystem()

    rag_system = st.session_state.rag_system

    # 文档上传
    uploaded_files = st.file_uploader(
        "上传文档",
        type=["txt", "pdf", "docx", "xlsx", "pptx"],
        accept_multiple_files=True,
        help="支持的格式：TXT, PDF, Word, Excel, PowerPoint"
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"📄 {uploaded_file.name}")
            with col2:
                if st.button(f"处理", key=f"process_{uploaded_file.name}"):
                    with st.spinner("正在处理文档..."):
                        success, message = rag_system.add_document(uploaded_file, uploaded_file.name)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                        st.rerun()

    # 显示文档统计
    stats = rag_system.get_document_stats()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("文档块数量", stats['total_chunks'])
    with col2:
        st.metric("关键词数量", stats['total_keywords'])
    with col3:
        st.metric("文档数量", len(stats['files']))

    # 显示已处理的文档列表
    if stats['files']:
        st.subheader("📋 已处理文档")
        for filename, chunk_count in stats['files'].items():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"📄 {filename} ({chunk_count} 个文档块)")
            with col2:
                if st.button("删除", key=f"delete_{filename}"):
                    rag_system.delete_document(filename)
                    st.success(f"已删除: {filename}")
                    st.rerun()


def enhance_query_with_rag(query, use_rag=True):
    """使用RAG增强查询"""
    if not use_rag or 'rag_system' not in st.session_state:
        return query, []

    rag_system = st.session_state.rag_system

    # 搜索相关文档
    relevant_chunks = rag_system.search_documents(query, top_k=3)

    if not relevant_chunks:
        return query, []

    # 生成增强的提示词
    enhanced_prompt = rag_system.generate_rag_prompt(query, relevant_chunks)

    return enhanced_prompt, relevant_chunks


# 测试函数
def test_rag_system():
    """测试RAG系统功能"""
    rag_system = RAGSystem()

    # 模拟文档内容
    test_content = """
    人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，旨在创造能够执行通常需要人类智能的任务的系统。
    机器学习是人工智能的一个子领域，它使计算机能够在没有明确编程的情况下学习和改进。
    深度学习是机器学习的一个分支，使用神经网络来模拟人脑的工作方式。
    自然语言处理（NLP）是人工智能的另一个重要分支，专注于让计算机理解和生成人类语言。
    """

    # 模拟文件对象
    class MockFile:
        def __init__(self, content, name):
            self.content = content
            self.name = name
            self.type = "text/plain"

        def getvalue(self):
            return self.content.encode('utf-8')

    mock_file = MockFile(test_content, "ai_knowledge.txt")

    # 添加文档
    success, message = rag_system.add_document(mock_file)
    print(f"添加文档: {success}, {message}")

    # 搜索测试
    queries = ["什么是机器学习？", "深度学习的原理", "NLP是什么"]

    for query in queries:
        print(f"\n查询: {query}")
        results = rag_system.search_documents(query)
        for i, result in enumerate(results):
            print(f"结果 {i + 1} (相关性: {result['relevance_score']:.2f}): {result['content'][:100]}...")


if __name__ == "__main__":
    test_rag_system()
