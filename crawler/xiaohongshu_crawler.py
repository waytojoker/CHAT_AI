import os
import time
import json
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from dotenv import load_dotenv

class XiaoHongShuCrawler:
    def __init__(self):
        self.setup_driver()
        self.data = []
        
    def setup_driver(self):
        """设置Chrome浏览器驱动"""
        chrome_options = Options()
        # chrome_options.add_argument('--headless')  # 注释掉无头模式
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={UserAgent().random}')
        # 添加以下选项来解决WebGL错误
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-webgl')
        chrome_options.add_argument('--disable-webgl2')
        chrome_options.add_argument('--disable-3d-apis')
        chrome_options.add_argument('--disable-gl-drawing-for-tests')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    def login(self):
        """登录小红书（需要手动扫码）"""
        self.driver.get('https://www.xiaohongshu.com')
        print("请在浏览器中手动扫码登录...")
        input("登录完成后按回车继续...")
        
        
    def crawl_user_posts(self, user_id, max_posts=50):
        """爬取指定用户的笔记"""
        url = f'https://www.xiaohongshu.com/user/profile/{user_id}'
        self.driver.get(url)
        
        # 等待页面加载
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'note-item'))
        )
        
        posts_count = 0
        while posts_count < max_posts:
            # 获取笔记列表
            posts = self.driver.find_elements(By.CLASS_NAME, 'note-item')
            
            for post in posts:
                if posts_count >= max_posts:
                    break
                    
                try:
                    # 获取笔记链接
                    link = post.find_element(By.TAG_NAME, 'a').get_attribute('href')
                    
                    # 获取笔记标题
                    try:
                        title = post.find_element(By.CLASS_NAME, 'title').text
                    except:
                        title = post.find_element(By.CLASS_NAME, 'content').text
                    
                    # 获取发布时间
                    try:
                        time_element = post.find_element(By.CLASS_NAME, 'time')
                        publish_time = time_element.text
                    except:
                        publish_time = "未知时间"
                    
                    # 获取互动数据
                    try:
                        interaction_data = post.find_elements(By.CLASS_NAME, 'interaction-info')
                        likes = interaction_data[0].text if len(interaction_data) > 0 else "0"
                        comments = interaction_data[1].text if len(interaction_data) > 1 else "0"
                        collects = interaction_data[2].text if len(interaction_data) > 2 else "0"
                    except:
                        likes = "0"
                        comments = "0"
                        collects = "0"
                    
                    post_data = {
                        'title': title,
                        'link': link,
                        'publish_time': publish_time,
                        'likes': likes,
                        'comments': comments,
                        'collects': collects
                    }
                    
                    self.data.append(post_data)
                    posts_count += 1
                    print(f"成功爬取第 {posts_count} 条笔记")
                    
                except Exception as e:
                    print(f"处理笔记时出错: {str(e)}")
                    continue
            
            # 滚动到页面底部加载更多
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # 增加等待时间，确保内容加载完成
            
            # 检查是否已经到达底部
            if len(self.data) >= max_posts:
                break
            
    def save_to_excel(self, filename='xiaohongshu_posts.xlsx'):
        """保存数据到Excel文件"""
        df = pd.DataFrame(self.data)
        df.to_excel(filename, index=False)
        print(f"数据已保存到 {filename}")
        
    def close(self):
        """关闭浏览器"""
        self.driver.quit()

def main():
    # 加载环境变量
    load_dotenv()
    
    # 创建爬虫实例
    crawler = XiaoHongShuCrawler()
    
    try:
        # 登录
        crawler.login()
        
        # 设置要爬取的用户ID（这里需要替换为实际的用户ID）
        user_id = "6499570c000000001f0053d3"
        
        # 爬取笔记
        crawler.crawl_user_posts(user_id, max_posts=50)
        
        # 保存数据
        crawler.save_to_excel()
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        crawler.close()

if __name__ == "__main__":
    main() 