import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from dotenv import load_dotenv

class XiaoHongShuDetailCrawler:
    def __init__(self):
        self.setup_driver()
        self.details = []
        
    def setup_driver(self):
        """设置Chrome浏览器驱动"""
        chrome_options = Options()
        # chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={UserAgent().random}')
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
        
    def crawl_note_detail(self, url):
        """爬取单篇笔记的详细内容"""
        try:
            self.driver.get(url)
            time.sleep(3)  # 等待页面加载
            
            # 等待内容加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'content'))
            )
            
            # 获取笔记标题
            try:
                title = self.driver.find_element(By.CLASS_NAME, 'title').text
            except:
                title = "无标题"
            
            # 获取笔记内容
            try:
                content = self.driver.find_element(By.CLASS_NAME, 'content').text
            except:
                content = "无内容"
            
            # 获取发布时间
            try:
                publish_time = self.driver.find_element(By.CLASS_NAME, 'publish-time').text
            except:
                publish_time = "未知时间"
            
            # 获取作者信息
            try:
                author = self.driver.find_element(By.CLASS_NAME, 'author').text
            except:
                author = "未知作者"
            
            # 获取标签
            try:
                tags = [tag.text for tag in self.driver.find_elements(By.CLASS_NAME, 'tag')]
            except:
                tags = []
            
            # 获取图片链接
            try:
                images = [img.get_attribute('src') for img in self.driver.find_elements(By.CLASS_NAME, 'note-image')]
            except:
                images = []
            
            # 获取互动数据
            try:
                likes = self.driver.find_element(By.CLASS_NAME, 'like-count').text
            except:
                likes = "0"
            
            try:
                comments = self.driver.find_element(By.CLASS_NAME, 'comment-count').text
            except:
                comments = "0"
            
            try:
                collects = self.driver.find_element(By.CLASS_NAME, 'collect-count').text
            except:
                collects = "0"
            
            note_detail = {
                'url': url,
                'title': title,
                'content': content,
                'publish_time': publish_time,
                'author': author,
                'tags': ','.join(tags),
                'images': ','.join(images),
                'likes': likes,
                'comments': comments,
                'collects': collects
            }
            
            self.details.append(note_detail)
            print(f"成功爬取笔记: {title}")
            return True
            
        except Exception as e:
            print(f"爬取笔记失败 {url}: {str(e)}")
            return False
    
    def save_to_excel(self, filename='xiaohongshu_details.xlsx'):
        """保存数据到Excel文件"""
        df = pd.DataFrame(self.details)
        df.to_excel(filename, index=False)
        print(f"详细数据已保存到 {filename}")
        
    def close(self):
        """关闭浏览器"""
        self.driver.quit()

def main():
    # 加载环境变量
    load_dotenv()
    
    # 读取原始Excel文件
    try:
        df = pd.read_excel('xiaohongshu_posts.xlsx')
        urls = df['link'].tolist()
    except Exception as e:
        print(f"读取Excel文件失败: {str(e)}")
        return
    
    # 创建爬虫实例
    crawler = XiaoHongShuDetailCrawler()
    
    try:
        # 登录
        crawler.login()
        
        # 爬取每篇笔记的详细内容
        for i, url in enumerate(urls, 1):
            print(f"\n正在爬取第 {i}/{len(urls)} 篇笔记...")
            crawler.crawl_note_detail(url)
            time.sleep(2)  # 添加延时，避免请求过快
        
        # 保存数据
        crawler.save_to_excel()
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        crawler.close()

if __name__ == "__main__":
    main() 