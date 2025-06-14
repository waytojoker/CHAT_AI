import requests
import pandas as pd
import time
import random
from bs4 import BeautifulSoup
import re

# 复用之前的User-Agent列表
user_agent_list = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36 115Browser/6.0.3',
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
    'Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0',
    'Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Mobile Safari/537.36",
]

def get_article_content(url):
    """获取文章内容"""
    try:
        headers = {
            'User-Agent': random.choice(user_agent_list)
        }
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取文章标题
            title = soup.find('h1', class_='rich_media_title').get_text().strip()
            
            # 获取文章内容
            content_div = soup.find('div', class_='rich_media_content')
            if content_div:
                # 移除所有script标签
                for script in content_div.find_all('script'):
                    script.decompose()
                
                # 获取纯文本内容
                content = content_div.get_text().strip()
                
                # 清理内容（移除多余的空行和空格）
                content = re.sub(r'\n\s*\n', '\n', content)
                content = re.sub(r'\s+', ' ', content)
                
                return {
                    'title': title,
                    'content': content
                }
    except Exception as e:
        print(f"爬取文章时出错: {str(e)}")
        return None

def main():
    # 读取之前保存的URL文件
    try:
        df = pd.read_csv('url.csv')
        
        # 创建新的DataFrame来存储文章内容
        articles_data = []
        
        # 遍历每个URL
        for index, row in df.iterrows():
            print(f"正在爬取第 {index + 1} 篇文章: {row['title']}")
            
            article = get_article_content(row['link'])
            if article:
                article_data = {
                    'title': article['title'],
                    'content': article['content'],
                    'original_link': row['link'],
                    'create_time': row['create_time']
                }
                articles_data.append(article_data)
                
                # 每爬取5篇文章保存一次
                if (index + 1) % 5 == 0:
                    save_df = pd.DataFrame(articles_data)
                    save_df.to_csv('articles_content.csv', mode='a', encoding='utf-8', index=False)
                    print(f"已保存 {index + 1} 篇文章")
                    articles_data = []
                
                # 随机延时，避免被封
                #time.sleep(random.randint(10, 20))
            else:
                print(f"无法获取文章内容: {row['title']}")
        
        # 保存剩余的文章
        if articles_data:
            save_df = pd.DataFrame(articles_data)
            save_df.to_csv('articles_content.csv', mode='a', encoding='utf-8', index=False)
            print("已保存所有剩余文章")
            
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main() 