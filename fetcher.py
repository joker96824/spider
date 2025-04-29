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