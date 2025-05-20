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

def get_card_links(url, search_keyword=None):
    """爬取主页面所有卡片的链接"""
    global driver
    
    # 如果driver不存在，创建新的实例
    if not driver:
        driver = webdriver.Edge()
    
    try:
        driver.get(url)
        
        # 如果有搜索关键词，先输入搜索内容
        if search_keyword:
            try:
                # 等待搜索框出现
                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "form-control.input-keywords.ant-input"))
                )
                # 输入搜索关键词
                search_input.clear()
                search_input.send_keys(search_keyword)
                time.sleep(1)  # 等待输入完成
            except Exception as e:
                print(f"输入搜索关键词失败：{e}")
                cleanup()
                return []
        
        # 等待并点击 class 为 submit 的按钮
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'submit'))
        )
        button.click()
        time.sleep(5)
    except Exception as e:
        print(f"按钮点击失败：{url}, {e}")
        cleanup()
        return []

    resp = driver.page_source
    soup = BeautifulSoup(resp, "html.parser")

    page_num = soup.find('li', class_='ant-pagination-total-text').get_text(strip=True)
    page_num = int(re.search(r'\d+', page_num).group()) // 20 + 1

    # 假设卡片链接在 class="card-link" 的 <a> 标签中
    links = []
    data = []
    count = 0
    for i in range(page_num):
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
            print({'序号':count,'code': code, 'link': link})
            count += 1
            
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
    
    # 根据是否有搜索关键词来决定文件名
    if search_keyword:
        # 将搜索关键词中的特殊字符替换为下划线
        safe_keyword = re.sub(r'[\\/:*?"<>|]', '_', search_keyword)
        filename = f'card_links_{safe_keyword}.xlsx'
    else:
        filename = 'card_links.xlsx'
    
    df.to_excel(filename, index=False)
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
        # 获取能力div
        ability_div = card_table.find('div', class_='valcol effect ant-col ant-col-24').find('div', class_='val')
        # 将能力文本按<br>分割成列表
        card_ability = []
        if ability_div:
            # 获取所有文本节点和<br>标签
            ability_str = ''
            for element in ability_div.contents:
                if element.name == 'br':
                    card_ability.append(ability_str)
                    ability_str = ''
                    continue
                # 获取文本内容并去除空白
                text = element.get_text(strip=True)
                if text:  # 只添加非空文本
                    ability_str += text
            card_ability.append(ability_str)
        data['能力'] = card_ability
    except Exception as e:
        print(f"获取能力时出错: {str(e)}")
        data['能力'] = []
        
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

def convert_to_sql(df, output_file='card_data.sql', search_keyword=None):
    """将DataFrame转换为PostgreSQL SQL文件"""
    # 根据搜索关键词修改输出文件名
    if search_keyword:
        # 将搜索关键词中的特殊字符替换为下划线
        safe_keyword = re.sub(r'[\\/:*?"<>|]', '_', search_keyword)
        # 获取文件名和扩展名
        file_name, file_ext = os.path.splitext(output_file)
        create_file = f"{file_name}_create{safe_keyword}{file_ext}"
        insert_file = f"{file_name}_insert{safe_keyword}{file_ext}"
    else:
        file_name, file_ext = os.path.splitext(output_file)
        create_file = f"{file_name}_create{file_ext}"
        insert_file = f"{file_name}_insert{file_ext}"
    
    # 准备API调用数据
    api_data = []
    
    # 列名映射
    column_mapping = {
        '代码': 'card_code',
        '链接': 'card_link',
        '编 号': 'card_number',
        '罕贵度': 'card_rarity',
        '中文名': 'name_cn',
        '日文名': 'name_jp',
        '国　家': 'nation',
        '种　族': 'clan',
        '等　级': 'grade',
        '技　能': 'skill',
        '力　量': 'card_power',
        '盾　护': 'shield',
        '☆　值': 'critical',
        '特殊标识': 'special_mark',
        '卡片类型': 'card_type',
        '触发类型': 'trigger_type',
        '别　称': 'card_alias',
        '集　团': 'card_group'
    }
    
    # 数字类型字段
    numeric_fields = ['等　级', '力　量', '盾　护', '☆　值']
    
    # 稀有度字段映射
    rarity_mapping = {
        '卡包': 'pack_name',
        '编号': 'card_number',
        '收录': 'release_info',
        '台词': 'quote',
        '绘师': 'illustrator',
        '图片': 'image_url'
    }
    
    # 创建表结构文件
    with open(create_file, 'w', encoding='utf-8') as f:
        # 写入创建表的SQL语句
        f.write("-- 创建Card表\n")
        f.write("DROP TABLE IF EXISTS Card CASCADE;\n")
        f.write("CREATE TABLE Card (\n")
        f.write("    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n")
        f.write("    card_code TEXT NOT NULL,\n")
        f.write("    card_link TEXT NOT NULL,\n")
        f.write("    card_number TEXT UNIQUE,\n")
        f.write("    card_rarity TEXT,\n")
        f.write("    name_cn TEXT,\n")
        f.write("    name_jp TEXT,\n")
        f.write("    nation TEXT,\n")
        f.write("    clan TEXT,\n")
        f.write("    grade INTEGER,\n")
        f.write("    skill TEXT,\n")
        f.write("    card_power INTEGER,\n")
        f.write("    shield INTEGER,\n")
        f.write("    critical INTEGER,\n")
        f.write("    special_mark TEXT,\n")
        f.write("    card_type TEXT,\n")
        f.write("    trigger_type TEXT,\n")
        f.write("    card_alias TEXT,\n")
        f.write("    card_group TEXT,\n")
        f.write("    ability TEXT,\n")
        f.write("    create_user_id TEXT NOT NULL DEFAULT current_user,\n")
        f.write("    update_user_id TEXT NOT NULL DEFAULT current_user,\n")
        f.write("    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n")
        f.write("    update_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n")
        f.write("    is_deleted BOOLEAN DEFAULT FALSE,\n")
        f.write("    card_version INTEGER DEFAULT 1,\n")
        f.write("    remark TEXT DEFAULT ''\n")
        f.write(");\n\n")

        # 添加Card表的注释
        f.write("COMMENT ON TABLE Card IS '卡牌基本信息表';\n")
        f.write("COMMENT ON COLUMN Card.id IS '主键ID';\n")
        f.write("COMMENT ON COLUMN Card.card_code IS '卡牌代码';\n")
        f.write("COMMENT ON COLUMN Card.card_link IS '卡牌链接';\n")
        f.write("COMMENT ON COLUMN Card.card_number IS '卡牌编号';\n")
        f.write("COMMENT ON COLUMN Card.card_rarity IS '卡牌罕贵度';\n")
        f.write("COMMENT ON COLUMN Card.name_cn IS '中文名称';\n")
        f.write("COMMENT ON COLUMN Card.name_jp IS '日文名称';\n")
        f.write("COMMENT ON COLUMN Card.nation IS '所属国家';\n")
        f.write("COMMENT ON COLUMN Card.clan IS '所属种族';\n")
        f.write("COMMENT ON COLUMN Card.grade IS '等级';\n")
        f.write("COMMENT ON COLUMN Card.skill IS '技能';\n")
        f.write("COMMENT ON COLUMN Card.card_power IS '力量值';\n")
        f.write("COMMENT ON COLUMN Card.shield IS '护盾值';\n")
        f.write("COMMENT ON COLUMN Card.critical IS '暴击值';\n")
        f.write("COMMENT ON COLUMN Card.special_mark IS '特殊标识';\n")
        f.write("COMMENT ON COLUMN Card.card_type IS '卡片类型';\n")
        f.write("COMMENT ON COLUMN Card.trigger_type IS '触发类型';\n")
        f.write("COMMENT ON COLUMN Card.card_alias IS '卡牌别称';\n")
        f.write("COMMENT ON COLUMN Card.card_group IS '所属集团';\n")
        f.write("COMMENT ON COLUMN Card.ability IS '能力描述';\n")
        f.write("COMMENT ON COLUMN Card.create_user_id IS '创建用户';\n")
        f.write("COMMENT ON COLUMN Card.update_user_id IS '更新用户';\n")
        f.write("COMMENT ON COLUMN Card.create_time IS '创建时间';\n")
        f.write("COMMENT ON COLUMN Card.update_time IS '更新时间';\n")
        f.write("COMMENT ON COLUMN Card.is_deleted IS '是否删除';\n")
        f.write("COMMENT ON COLUMN Card.card_version IS '版本号';\n")
        f.write("COMMENT ON COLUMN Card.remark IS '备注信息';\n\n")
        
        # 创建CardAbility表
        f.write("-- 创建CardAbility表\n")
        f.write("DROP TABLE IF EXISTS CardAbility CASCADE;\n")
        f.write("CREATE TABLE CardAbility (\n")
        f.write("    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n")
        f.write("    card_id UUID REFERENCES Card(id) ON DELETE CASCADE,\n")
        f.write("    ability_desc TEXT NOT NULL,\n")
        f.write("    ability JSONB DEFAULT '{}',\n")
        f.write("    create_user_id TEXT NOT NULL DEFAULT current_user,\n")
        f.write("    update_user_id TEXT NOT NULL DEFAULT current_user,\n")
        f.write("    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n")
        f.write("    update_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP\n")
        f.write(");\n\n")

        # 添加CardAbility表的注释
        f.write("COMMENT ON TABLE CardAbility IS '卡牌技能表';\n")
        f.write("COMMENT ON COLUMN CardAbility.id IS '主键ID';\n")
        f.write("COMMENT ON COLUMN CardAbility.card_id IS '关联的卡牌ID';\n")
        f.write("COMMENT ON COLUMN CardAbility.ability_desc IS '技能描述';\n")
        f.write("COMMENT ON COLUMN CardAbility.ability IS '技能JSON数据';\n")
        f.write("COMMENT ON COLUMN CardAbility.create_user_id IS '创建用户';\n")
        f.write("COMMENT ON COLUMN CardAbility.update_user_id IS '更新用户';\n")
        f.write("COMMENT ON COLUMN CardAbility.create_time IS '创建时间';\n")
        f.write("COMMENT ON COLUMN CardAbility.update_time IS '更新时间';\n\n")
        
        # 创建CardRarity表
        f.write("-- 创建CardRarity表\n")
        f.write("DROP TABLE IF EXISTS CardRarity CASCADE;\n")
        f.write("CREATE TABLE CardRarity (\n")
        f.write("    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n")
        f.write("    card_id UUID REFERENCES Card(id) ON DELETE CASCADE,\n")
        f.write("    pack_name TEXT,\n")
        f.write("    card_number TEXT,\n")
        f.write("    release_info TEXT,\n")
        f.write("    quote TEXT,\n")
        f.write("    illustrator TEXT,\n")
        f.write("    image_url TEXT,\n")
        f.write("    create_user_id TEXT NOT NULL DEFAULT current_user,\n")
        f.write("    update_user_id TEXT NOT NULL DEFAULT current_user,\n")
        f.write("    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n")
        f.write("    update_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n")
        f.write("    UNIQUE(pack_name, card_number)\n")
        f.write(");\n\n")

        # 添加CardRarity表的注释
        f.write("COMMENT ON TABLE CardRarity IS '卡牌稀有度信息表';\n")
        f.write("COMMENT ON COLUMN CardRarity.id IS '主键ID';\n")
        f.write("COMMENT ON COLUMN CardRarity.card_id IS '关联的卡牌ID';\n")
        f.write("COMMENT ON COLUMN CardRarity.pack_name IS '卡包名称';\n")
        f.write("COMMENT ON COLUMN CardRarity.card_number IS '卡包内编号';\n")
        f.write("COMMENT ON COLUMN CardRarity.release_info IS '收录信息';\n")
        f.write("COMMENT ON COLUMN CardRarity.quote IS '卡牌台词';\n")
        f.write("COMMENT ON COLUMN CardRarity.illustrator IS '绘师';\n")
        f.write("COMMENT ON COLUMN CardRarity.image_url IS '卡牌图片URL';\n")
        f.write("COMMENT ON COLUMN CardRarity.create_user_id IS '创建用户';\n")
        f.write("COMMENT ON COLUMN CardRarity.update_user_id IS '更新用户';\n")
        f.write("COMMENT ON COLUMN CardRarity.create_time IS '创建时间';\n")
        f.write("COMMENT ON COLUMN CardRarity.update_time IS '更新时间';\n\n")
        
        # 创建索引
        f.write("-- 创建索引\n")
        f.write("CREATE INDEX idx_card_code ON Card(card_code);\n")
        f.write("CREATE INDEX idx_card_name_cn ON Card(name_cn);\n")
        f.write("CREATE INDEX idx_card_name_jp ON Card(name_jp);\n")
        f.write("CREATE INDEX idx_card_create_time ON Card(create_time);\n")
        f.write("CREATE INDEX idx_card_update_time ON Card(update_time);\n")
        f.write("CREATE INDEX idx_card_ability_card_id ON CardAbility(card_id);\n")
        f.write("CREATE INDEX idx_card_rarity_card_id ON CardRarity(card_id);\n")
        f.write("CREATE INDEX idx_card_rarity_pack_name ON CardRarity(pack_name);\n")
        f.write("CREATE INDEX idx_card_rarity_illustrator ON CardRarity(illustrator);\n\n")
    
    # 创建数据插入文件
    with open(insert_file, 'w', encoding='utf-8') as f:
        # 写入插入数据的SQL语句
        f.write("-- 插入数据\n")
        for _, row in df.iterrows():
            # 准备API数据
            api_card = {}
            
            # 插入Card表
            card_columns = []
            card_values = []
            remark = []  # 用于收集备注信息
            
            # 添加基本字段
            for cn_name, en_name in column_mapping.items():
                if cn_name in df.columns:
                    value = row[cn_name]
                    if pd.isna(value) or value == '-':
                        # 对于card_code和card_link，不允许为NULL
                        if en_name in ['card_code', 'card_link']:
                            print(f"警告：{row['代码'] if '代码' in row else '未知'}的{cn_name}为空")
                            continue
                        value = 'NULL'
                        api_card[en_name] = None
                    else:
                        # 处理数字类型字段
                        if cn_name in numeric_fields:
                            try:
                                # 尝试转换为整数
                                value = int(value)
                                value = str(value)  # 转换为字符串，因为SQL语句需要
                                api_card[en_name] = int(value)
                            except (ValueError, TypeError):
                                # 特殊处理力量字段的"15000+"情况
                                if cn_name == '力　量' and value == '15000+':
                                    value = '15000'
                                    remark.append('力量: 15000+')
                                    api_card[en_name] = 15000
                                else:
                                    print(f"{row['代码']}数据处理失败{cn_name}： {value}")
                                    value = 'NULL'
                                    api_card[en_name] = None
                        else:
                            # 转义单引号
                            value = str(value).replace("'", "''")
                            value = f"'{value}'"
                            api_card[en_name] = str(value).strip("'")
                    
                    card_columns.append(en_name)
                    card_values.append(value)
                else:
                    # 如果字段在映射中但不在DataFrame中，添加NULL值
                    card_columns.append(column_mapping[cn_name])
                    card_values.append('NULL')
                    api_card[en_name] = None
            
            # 处理能力字段
            if '能力' in df.columns and not pd.isna(row['能力']):
                try:
                    # 将能力字符串转换为列表
                    if isinstance(row['能力'], str):
                        ability_list = ast.literal_eval(row['能力'])
                    else:
                        ability_list = row['能力']
                    
                    if isinstance(ability_list, list):
                        # 将所有能力描述合并为一个字符串，用换行符分隔
                        ability_text = '\n'.join(ability_list)
                        # 转义单引号
                        ability_text = ability_text.replace("'", "''")
                        # 添加到Card表
                        card_columns.append('ability')
                        card_values.append(f"'{ability_text}'")
                        api_card['ability'] = ability_text
                except Exception as e:
                    print(f"处理能力数据时出错: {str(e)}")
                    card_columns.append('ability')
                    card_values.append('NULL')
                    api_card['ability'] = None
            else:
                card_columns.append('ability')
                card_values.append('NULL')
                api_card['ability'] = None
            
            # 添加操作者相关字段
            card_columns.extend(['create_user_id', 'update_user_id', 'create_time', 'update_time', 'is_deleted', 'card_version', 'remark'])
            card_values.extend([
                'current_user',  # create_user_id
                'current_user',  # update_user_id
                'CURRENT_TIMESTAMP',  # create_time
                'CURRENT_TIMESTAMP',  # update_time
                'FALSE',  # is_deleted
                '1',  # card_version
                f"'{'; '.join(remark)}'" if remark else "''"  # 如果有备注则添加，否则为空字符串
            ])
            
            # 先插入Card表并获取ID
            f.write("DO $$\n")
            f.write("DECLARE\n")
            f.write("    v_card_id UUID;\n")
            f.write("BEGIN\n")
            f.write(f"    INSERT INTO Card ({', '.join(card_columns)}) VALUES ({', '.join(card_values)}) RETURNING id INTO v_card_id;\n\n")
            
            # 准备API数据的能力信息
            api_card['ability_infos'] = []
            
            # 插入CardAbility表
            if '能力' in df.columns and not pd.isna(row['能力']):
                try:
                    # 将能力字符串转换为列表
                    if isinstance(row['能力'], str):
                        ability_list = ast.literal_eval(row['能力'])
                    else:
                        ability_list = row['能力']
                    
                    if isinstance(ability_list, list):
                        for ability in ability_list:
                            # 转义单引号
                            ability_desc = str(ability).replace("'", "''")
                            f.write(f"    INSERT INTO CardAbility (card_id, ability_desc, create_user_id, update_user_id) VALUES (v_card_id, '{ability_desc}', current_user, current_user);\n")
                            
                            # 添加到API数据
                            api_card['ability_infos'].append({
                                'ability_desc': ability,
                                'ability': {}  # 默认空对象
                            })
                except Exception as e:
                    print(f"处理能力数据时出错: {str(e)}")
            
            # 准备API数据的稀有度信息
            api_card['rarity_infos'] = []
            
            # 插入CardRarity表
            if '稀有度' in df.columns and not pd.isna(row['稀有度']):
                try:
                    rarity_list = ast.literal_eval(row['稀有度'])
                    for rarity in rarity_list:
                        rarity_columns = ['card_id', 'create_user_id', 'update_user_id']
                        rarity_values = ['v_card_id', 'current_user', 'current_user']  # 使用变量而不是函数调用
                        
                        rarity_info = {}
                        for old_key, new_key in rarity_mapping.items():
                            if old_key in rarity:
                                value = rarity[old_key]
                                if pd.isna(value) or value == '-':
                                    value = 'NULL'
                                    rarity_info[new_key] = None
                                else:
                                    # 转义单引号
                                    value = str(value).replace("'", "''")
                                    value = f"'{value}'"
                                    rarity_info[new_key] = str(value).strip("'")
                                
                                rarity_columns.append(new_key)
                                rarity_values.append(value)
                        
                        f.write(f"    INSERT INTO CardRarity ({', '.join(rarity_columns)}) VALUES ({', '.join(rarity_values)});\n")
                        
                        # 添加到API数据
                        api_card['rarity_infos'].append(rarity_info)
                except:
                    pass
            
            f.write("END $$;\n\n")
            
            # 添加到API数据列表
            api_data.append(api_card)
    
    # 调用API上传数据
    if api_data:
        try:
            url = "http://118.25.45.131:8000/api/v1/card_import/import/batch"
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=api_data, headers=headers)
            if response.status_code == 200:
                print(f"API调用成功: {response.json()}")
            else:
                print(f"API调用失败，状态码: {response.status_code}")
                print(f"错误信息: {response.text}")
        except Exception as e:
            print(f"API调用失败: {str(e)}")
            print("请确保API服务已启动并正常运行")
    
    print(f"SQL文件已生成: {create_file}, {insert_file}")
    return create_file, insert_file 