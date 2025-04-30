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

# 全局webdriver实例
driver = None

def cleanup():
    """清理函数，确保webdriver被正确关闭"""
    global driver
    if driver:
        try:
            driver.quit()
        except:
            pass
        driver = None

# 注册退出时的清理函数
atexit.register(cleanup)

def get_card_links(url):
    """爬取主页面所有卡片的链接"""
    global driver
    
    # 如果driver不存在，创建新的实例
    if not driver:
        driver = webdriver.Edge()
    
    try:
        driver.get(url)
        # 等待并点击 class 为 submit 的按钮
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'submit'))
        )
        button.click()
        time.sleep(5)
    except Exception as e:
        print(f"按钮点击失败：{url}, {e}")
        cleanup()

    resp = driver.page_source
    soup = BeautifulSoup(resp, "html.parser")

    page_num = soup.find('li', class_='ant-pagination-total-text').get_text(strip=True)
    page_num = int(re.search(r'\d+', page_num).group()) // 20 + 1

    # 假设卡片链接在 class="card-link" 的 <a> 标签中
    links = []
    data = []
    for i in range(page_num - 1):
        resp = driver.page_source
        soup = BeautifulSoup(resp, "html.parser")
        divs = soup.find_all('div', class_='ant-col ant-col-24 ant-col-lg-20 ant-col-lg-pull-4')
        print(len(divs))
        for div in divs:
            # 获取 code
            meta_div = div.find('div', class_='meta head clearfix')
            code = meta_div.get_text(strip=True) if meta_div else ''
            
            # 获取 link
            h2 = div.find('h2')
            a = h2.find('a') if h2 else None
            href = a.get('href') if a else ''
            link = f"https://vgcard.yimieji.com{href}" if href else ''
            
            # 添加到数据列表
            data.append({'code': code, 'link': link})
            print({'code': code, 'link': link})
            
            if href:
                # 这里可根据实际情况补全域名
                links.append(href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/"))
        if i < page_num - 1:
            try:
                # 等待并点击 title 为 "Next Page" 的按钮
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, 'ant-pagination-next'))
                )
                
                next_button.click()
                time.sleep(5)  # 等待页面加载
            except Exception as e:
                print(f"下一页按钮点击失败：{e}")
                cleanup()
    # 保存到 DataFrame 并导出 xlsx
    df = pd.DataFrame(data)
    df.to_excel('card_links.xlsx', index=False)
    return links

def fetch_card_page(url):
    """爬取单个卡片页面"""
    data = {}
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find('article', class_='detail')
    card_table = table.find('div', class_='card row ant-row')
    rare_table = table.find_all('div', class_='packTable row ant-row')
    
    # 修改base_info的获取方式
    base_info = card_table.find('div', class_='row ant-row').find_all('div', class_='valcol')
    
    for info in base_info:
        try:
            title = info.find('div', class_='head symbolHead').get_text(strip=True)
            value = info.find('div', class_='val').get_text(strip=True)
            data[title] = value
        except Exception as e:
            print(f"获取信息时出错: {str(e)}")
            continue
            
    try:
        card_ability = card_table.find('div', class_='valcol effect ant-col ant-col-24').find('div', class_='val').get_text(strip=True)
        data['能力'] = card_ability
    except Exception as e:
        print(f"获取能力时出错: {str(e)}")
        
    rare_list = []
    for rare in rare_table:
        try:
            rare_info = {}
            rare_rows = rare.find('tbody').find_all('tr')
            for row in rare_rows:
                title = row.th.get_text(strip=True)
                value = row.td.get_text(strip=True)
                rare_info[title] = value
            
            image_info = rare.find('div', class_='packCardImg').img
            image_url = image_info.get('data-src') if image_info else ''
            rare_info['图片'] = image_url

            rare_list.append(rare_info)
        except Exception as e:
            print(f"获取稀有度信息时出错: {str(e)}")
            continue

    data['稀有度'] = rare_list
    return data

def download_card_images(df, output_dir='card_images'):
    """下载卡片图片"""
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 下载进度
    total = len(df)
    downloaded = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        try:
            # 获取图片URL
            rare_list = row['稀有度']
            # 如果rare_list是字符串，尝试将其转换为字典列表
            if isinstance(rare_list, str):
                try:
                    # 使用json.loads将字符串转换为Python对象
                    rare_list = ast.literal_eval(rare_list)
                    # 确保转换后的对象是列表
                    if not isinstance(rare_list, list):
                        rare_list = []
                except:
                    rare_list = []
            
            if not isinstance(rare_list, list):
                continue
                
            for rare in rare_list:
                if '图片' in rare and rare['图片']:
                    image_url = rare['图片']
                    # 处理文件名中的"/"
                    filename = rare['编号']
                    parts = filename.split('/')
                    if len(parts) > 1:
                        # 创建子文件夹
                        sub_dir = os.path.join(output_dir, parts[0])
                        if not os.path.exists(sub_dir):
                            os.makedirs(sub_dir)
                        # 完整的文件路径
                        file_path = os.path.join(sub_dir, f"{parts[1]}.jpg")
                    else:
                        # 如果没有"/"，直接保存在output_dir下
                        file_path = os.path.join(output_dir, f"{filename}.jpg")
                    
                    # 检查文件是否已存在
                    if os.path.exists(file_path):
                        print(f"图片已存在，跳过: {file_path}")
                        skipped += 1
                        continue
                    
                    # 下载图片
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        with open(file_path, 'wb') as f:
                            f.write(response.content)
                        downloaded += 1
                        print(f"已下载图片: {file_path}")
        except Exception as e:
            print(f"下载图片时出错: {str(e)}")
            continue
    
    print(f"下载完成！成功下载: {downloaded}，跳过: {skipped}，总计: {total}")
    return downloaded, total 