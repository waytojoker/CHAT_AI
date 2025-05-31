# 爬取公开公众号链接
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.edge.options import Options
from flask import Flask, request, jsonify

#数据清洗处理
def process_wechat_article(url):
    # driver = webdriver.Edge();
    #隐藏edge窗口，采用无头模式隐藏
    # 1. 创建配置对象
    edge_options = Options()
    edge_options.add_argument('--edge-skip-compat-layer-relaunch')#忽略兼容性检查
    edge_options.add_argument("--window-position=-32000,-32000")  # 将窗口移到屏幕外
    # 2. 添加无头模式参数
    # edge_options.add_argument("--headless")  # 无头模式
    # edge_options.add_argument("--disable-gpu")  # 禁用GPU加速（可选）
    # edge_options.add_argument("--no-sandbox")  # Linux系统可能需要
    # edge_options.add_argument("--disable-blink-features=AutomationControlled")
    # #无头模式速率优化
    # edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # edge_options.add_experimental_option("useAutomationExtension", False)
    # edge_options.add_argument("--disable-software-rasterizer")
    # edge_options.add_argument("--disable-dev-shm-usage")
    # edge_options.page_load_strategy = "eager"  # 只等待DOM加载
    # 3. 直接传递options参数（无需Service）
    driver = webdriver.Edge(options=edge_options)
    driver.get(url)
    data_text = ""
    # 等待目标内容加载（例如：文章正文）
    try:
        # 1. 获取标题
        title = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "rich_media_title"))
        ).text.strip()
        # 2. 获取正文
        content = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "rich_media_content"))
        )

        # 3. 处理正文内容
        # 先获取文本

        content_text = content.text.strip()

        # 移除时间标记
        cleaned_text = re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', '', content_text)

        # 定义终止关键词列表
        stop_keywords = [
            "本文来源", "小程序", "来源：", "来源/",
            "©", "编辑/", "监制/", "文案 |",
            "排版 |", "审核 |", "编辑 |", "监制 |", "来源 |",
            "策划丨", "作者丨", "图片来源丨",
            "策划 |", "作者 |", "微信编辑 设计排版丨","总台央视记者/"
        ]

        # 逐行检查，跳过含有关键词的行但继续处理
        cleaned_lines = []
        for line in cleaned_text.split("\n"):
            line = line.strip()
            if not line:
                continue  # 跳过空行

            # 检查是否包含关键词（不立即终止）
            if any(keyword in line for keyword in stop_keywords):
                continue  # 跳过当前行，继续下一行

            cleaned_lines.append(line)  # 保留无关键词的行

        # 合并有效行
        cleaned_text = "\n".join(cleaned_lines)
        # print(cleaned_text)
        # 去除多余空行
        cleaned_text = "\n".join(line.strip() for line in cleaned_text.split("\n") if line.strip())
        # 5. 合并标题和过滤后的正文
        # print(title)
        cleaned_text = f"{title}\n\n{cleaned_text}"
        # print(cleaned_text)
        data_text = cleaned_text
    finally:
        driver.quit()
    #输出清洗后的爬取内容
    print(data_text)
    return data_text



app = Flask(__name__)
url = ""


@app.route('/', methods=['GET'])

def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>URL Processor</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
            #urlInput { width: 100%; padding: 10px; margin-bottom: 10px; }
            button { padding: 10px 20px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
            button:hover { background-color: #45a049; }
            #result { margin-top: 20px; padding: 15px; border: 1px solid #ddd; }
        </style>
    </head>
    <body>
        <h1>URL Processor</h1>
        <input type="text" id="urlInput" placeholder="Enter URL">
        <button onclick="processUrl()">Process URL</button>
        <div id="result"></div>
        <script>
            async function processUrl() {
                const url = document.getElementById('urlInput').value;
                const resultDiv = document.getElementById('result');
                resultDiv.innerHTML = 'Processing...';

                try {
                    const response = await fetch('/process_url', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: url })
                    });
                    const data = await response.json();
                    resultDiv.innerHTML = `
                        <h3>Results:</h3>
                        <p>URL: ${data.url}</p>
                        <p>Title: ${data.title}</p>
                        <p>Content: ${data.content}</p>
                    `;
                } catch (error) {
                    resultDiv.innerHTML = `Error: ${error.message}`;
                }
            }
        </script>
    </body>
    </html>
    """


@app.route('/process_url', methods=['POST'])
#处理url
def process_url():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    # 这里只是返回接收到的URL作为示例
    # 你可以添加自己的处理逻辑
    # 处理微信公众号文章
    article_content = process_wechat_article(url)

    return jsonify({
        'status': 'success',
        'url': url,
        'title': article_content.split('\n')[0] if article_content else 'No title',
        'content': article_content
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
#测试url
# url = "https://mp.weixin.qq.com/s/DN2Lwe9v1_rAdMq0CdNW5Q"
# url = "https://mp.weixin.qq.com/s/WmXJ6j122fW-VyRma-KtxQ"
# question_text = "这篇文章有哪些错别字，请分别按照错别字个数，按行列出来，要求输出在哪一句中有错别字，并进行更改"