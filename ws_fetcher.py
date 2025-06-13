import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import pandas as pd
import re
import atexit
import os
import json
import ast
from urllib.parse import urlparse
from selenium.common.exceptions import WebDriverException
import random

def create_driver():
    """创建并配置Edge浏览器实例"""
    options = webdriver.EdgeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-logging')
    options.add_argument('--log-level=3')
    options.add_argument('--silent')
    
    # 设置页面加载策略
    options.page_load_strategy = 'eager'
    
    return webdriver.Edge(options=options)

def retry_on_failure(max_retries=3, delay=2):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except WebDriverException as e:
                    if attempt == max_retries - 1:
                        raise e
                    print(f"尝试 {attempt + 1}/{max_retries} 失败，{delay}秒后重试...")
                    time.sleep(delay + random.uniform(0, 1))  # 添加随机延迟
            return None
        return wrapper
    return decorator

@retry_on_failure(max_retries=3, delay=2)
def get_card_links(url, search_keyword=None):
    """获取卡片链接列表"""
    driver = None
    try:
        driver = create_driver()
        driver_pid = driver.service.process.pid
        
        # 设置页面加载超时
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(30)
        
        # 访问页面
        driver.get(url)
        
        # 等待页面加载
        time.sleep(3)
        
        # 先找到搜索结果表格容器
        table_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "search-result-table-container"))
        )
        
        # 在容器中查找table
        table = table_container.find_element(By.TAG_NAME, "table")
        
        # 在table中查找tbody
        tbody = table.find_element(By.TAG_NAME, "tbody")
        
        # 在tbody中查找所有tr
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        print(f"找到 {len(rows)} 行数据")
        
        all_cards = []
        # 处理每一行数据
        for row in rows:
            try:
                # 获取图片链接
                img = row.find_element(By.CSS_SELECTOR, "th a img")
                img_src = img.get_attribute('src')
                img_url = "https://ws-tcg.com" + img_src if img_src.startswith('/') else img_src
                img_name = img_url.split('/')[-1].split('.')[0]
                
                # 获取卡片名和代码
                card_info = row.find_element(By.CSS_SELECTOR, "td h4 a")
                spans = card_info.find_elements(By.TAG_NAME, "span")
                card_name = spans[0].text if len(spans) > 0 else ""
                card_code = spans[1].text if len(spans) > 1 else ""
                
                # 获取卡片属性
                td = row.find_element(By.TAG_NAME, "td")
                attr_spans = td.find_elements(By.XPATH, "./span")
                
                # 获取阵营
                try:
                    faction_img = attr_spans[0].find_element(By.TAG_NAME, "img")
                    faction_src = faction_img.get_attribute('src')
                    faction_url = "https://ws-tcg.com" + faction_src if faction_src.startswith('/') else faction_src
                    faction = faction_url.split('/')[-1].split('.')[0]
                    faction = "白" if faction == "w" else "黑"
                except:
                    faction = ""
                
                # 获取卡片种类
                card_type = attr_spans[1].text.split('：')[-1] if len(attr_spans) > 1 else ""
                card_type_map = {
                    "キャラ": "角色",
                    "イベント": "事件",
                    "クライマックス": "高潮"
                }
                card_type = card_type_map.get(card_type, card_type)
                
                # 获取等级
                level = attr_spans[2].text.split('：')[-1] if len(attr_spans) > 2 else ""
                
                # 获取颜色
                try:
                    color_img = attr_spans[3].find_element(By.TAG_NAME, "img")
                    color_src = color_img.get_attribute('src')
                    color_url = "https://ws-tcg.com" + color_src if color_src.startswith('/') else color_src
                    color = color_url.split('/')[-1].split('.')[0]
                    color_map = {
                        "yellow": "黄",
                        "red": "红",
                        "blue": "蓝",
                        "green": "绿"
                    }
                    color = color_map.get(color, color)
                except:
                    color = ""
                
                # 获取攻击力
                power = attr_spans[4].text.split('：')[-1] if len(attr_spans) > 4 else ""
                
                # 获取魂伤
                try:
                    soul_imgs = attr_spans[5].find_elements(By.TAG_NAME, "img")
                    soul = []
                    for img in soul_imgs:
                        src = img.get_attribute('src')
                        url = "https://ws-tcg.com" + src if src.startswith('/') else src
                        soul.append(url.split('/')[-1].split('.')[0])
                except:
                    soul = []
                
                # 获取费用
                cost = attr_spans[6].text.split('：')[-1] if len(attr_spans) > 6 else ""
                
                # 获取稀有度
                rarity = attr_spans[7].text.split('：')[-1] if len(attr_spans) > 7 else ""
                
                # 获取判定
                try:
                    trigger_imgs = attr_spans[8].find_elements(By.TAG_NAME, "img")
                    trigger = [img.get_attribute('src') for img in trigger_imgs]
                except:
                    trigger = []
                
                # 获取特征
                traits = attr_spans[9].text.split('：')[-1] if len(attr_spans) > 9 else ""
                
                # 获取台词
                flavor = attr_spans[10].text.split('：')[-1] if len(attr_spans) > 10 else ""
                
                # 获取技能
                ability = attr_spans[11].get_attribute('innerHTML') if len(attr_spans) > 11 else ""
                
                # 保存卡片数据
                card_data = {
                    "图片": img_url,
                    "卡片名": card_name,
                    "卡片代码": card_code,
                    "阵营": faction,
                    "卡片种类": card_type,
                    "等级": level,
                    "颜色": color,
                    "攻击力": power,
                    "魂伤": soul,
                    "费用": cost,
                    "稀有度": rarity,
                    "判定": trigger,
                    "特征": traits,
                    "台词": flavor,
                    "技能": ability
                }
                all_cards.append(card_data)
                
            except Exception as e:
                print(f"处理行数据时出错: {str(e)}")
                continue
        
        return all_cards, driver_pid
    except Exception as e:
        print(f"获取链接时出错: {str(e)}")
        if driver:
            driver.quit()
        return [], None
    finally:
        if driver:
            driver.quit()

def save_to_excel(cards, filename="ws_cards.xlsx"):
    """保存数据到Excel文件"""
    df = pd.DataFrame(cards)
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"\n数据已保存到 {filename}")

def check_and_create_excel(filename="ws_cards.xlsx"):
    """检查并创建Excel文件"""
    if not os.path.exists(filename):
        # 创建空的DataFrame，设置列名
        columns = [
            "图片", "卡片名", "卡片代码", "阵营", "卡片种类", "等级", 
            "颜色", "攻击力", "魂伤", "费用", "稀有度", "判定", 
            "特征", "台词", "技能"
        ]
        df = pd.DataFrame(columns=columns)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"创建新文件: {filename}")
    return pd.read_excel(filename)

def fetch_all_pages(total_pages, should_stop=None):
    """获取所有页面的数据"""
    filename = "ws_cards.xlsx"
    base_url = "https://ws-tcg.com/cardlist/search?page={}"
    
    for page in range(1, total_pages + 1):
        if should_stop and should_stop():
            return
            
        print(f"\n正在获取第 {page} 页数据...")
        
        # 读取Excel文件
        df = check_and_create_excel(filename)
        
        # 计算当前页面的数据应该插入的位置
        start_row = (page - 1) * 25
        
        # 检查这个位置的数据是否为空
        if start_row >= len(df) or pd.isna(df.iloc[start_row]['卡片名']):
            print(f"第 {page} 页数据不存在，开始爬取...")
            url = base_url.format(page)
            page_cards, driver_pid = get_card_links(url)
            
            if page_cards:
                # 将新数据转换为DataFrame
                new_df = pd.DataFrame(page_cards)
                
                # 如果DataFrame长度不足，扩展它
                if len(df) < start_row + len(new_df):
                    df = pd.concat([df, pd.DataFrame(columns=df.columns, index=range(len(df), start_row + len(new_df)))])
                
                # 将新数据插入到对应位置
                df.iloc[start_row:start_row + len(new_df)] = new_df.values
                
                # 保存更新后的数据
                df.to_excel(filename, index=False, engine='openpyxl')
                print(f"第 {page} 页数据已保存，当前共有 {len(df)} 行数据")
            else:
                print(f"第 {page} 页获取失败，跳过")
        else:
            print(f"第 {page} 页数据已存在，跳过")

if __name__ == "__main__":
    # 获取用户输入的总页数
    while True:
        try:
            total_pages = int(input("请输入要爬取的总页数（数字）："))
            if total_pages > 0:
                break
            else:
                print("请输入大于0的数字")
        except ValueError:
            print("请输入有效的数字")
    
    # 获取所有页面的数据
    fetch_all_pages(total_pages) 