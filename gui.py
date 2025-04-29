import tkinter as tk
from tkinter import ttk, scrolledtext
from fetcher import get_card_links, fetch_card_page, cleanup
import threading
import pandas as pd
import os
import sys

class SpiderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("卡片爬虫")
        self.root.geometry("600x400")
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 创建按钮
        self.btn_get_links = ttk.Button(root, text="获取卡片链接", command=self.start_get_links)
        self.btn_get_links.pack(pady=10)
        
        self.btn_fetch_pages = ttk.Button(root, text="爬取卡片页面", command=self.start_fetch_pages)
        self.btn_fetch_pages.pack(pady=10)
        
        # 创建复选框
        self.skip_existing = tk.BooleanVar(value=True)
        self.skip_checkbox = ttk.Checkbutton(root, text="跳过已爬取的内容", variable=self.skip_existing)
        self.skip_checkbox.pack(pady=5)
        
        # 创建进度条
        self.progress = ttk.Progressbar(root, length=400, mode='determinate')
        self.progress.pack(pady=10)
        
        # 创建显示框
        self.text_area = scrolledtext.ScrolledText(root, width=60, height=15)
        self.text_area.pack(pady=10)
        
        # 初始化变量
        self.card_links = []
        self.url = "https://vgcard.yimieji.com/"
        self.is_closing = False
        
    def on_closing(self):
        """窗口关闭时的处理函数"""
        self.is_closing = True
        self.log("正在关闭程序，请稍候...")
        # 等待所有线程完成
        for thread in threading.enumerate():
            if thread != threading.current_thread():
                thread.join(timeout=1.0)
        # 清理资源
        cleanup()
        self.root.destroy()
        sys.exit(0)
        
    def log(self, message):
        """在文本框中显示日志"""
        if not self.is_closing:
            self.text_area.insert(tk.END, message + "\n")
            self.text_area.see(tk.END)
        
    def start_get_links(self):
        """启动获取链接的线程"""
        if self.is_closing:
            return
        self.btn_get_links.config(state='disabled')
        self.log("开始获取卡片链接...")
        thread = threading.Thread(target=self.get_links_thread)
        thread.start()
        
    def get_links_thread(self):
        """获取链接的线程函数"""
        try:
            self.card_links = get_card_links(self.url)
            if not self.is_closing:
                self.log(f"成功获取 {len(self.card_links)} 个卡片链接")
        except Exception as e:
            if not self.is_closing:
                self.log(f"获取链接时出错: {str(e)}")
        finally:
            if not self.is_closing:
                self.btn_get_links.config(state='normal')
            
    def start_fetch_pages(self):
        """启动爬取页面的线程"""
        if self.is_closing:
            return
        if not os.path.exists('card_links.xlsx'):
            self.log("请先获取卡片链接并生成card_links.xlsx文件！")
            return
            
        self.btn_fetch_pages.config(state='disabled')
        self.log("开始爬取卡片页面...")
        thread = threading.Thread(target=self.fetch_pages_thread)
        thread.start()
        
    def fetch_pages_thread(self):
        """爬取页面的线程函数"""
        try:
            # 读取card_links.xlsx
            df = pd.read_excel('card_links.xlsx')
            
            # 如果card_info.xlsx不存在，则创建并初始化
            if not os.path.exists('card_info.xlsx'):
                self.log("创建新的card_info.xlsx文件...")
                # 创建包含所有必要列的DataFrame
                columns = [
                    '代码', '链接', '编号', '罕贵度', '中文名', '日文名', '国家', 
                    '种族', '等级', '技能', '力量', '盾护', '☆值', '特殊标识', 
                    '卡片类型', '触发类型', '能力', '解说', '赛制类型'
                ]
                result_df = pd.DataFrame(columns=columns)
                # 初始化数据
                for _, row in df.iterrows():
                    result_df = pd.concat([
                        result_df, 
                        pd.DataFrame([{
                            '代码': row['code'],
                            '链接': row['link']
                        }])
                    ], ignore_index=True)
                result_df.to_excel('card_info.xlsx', index=False)
                self.log("已创建新的card_info.xlsx文件")
            
            # 读取card_info.xlsx
            result_df = pd.read_excel('card_info.xlsx')
            total = len(result_df)
            self.progress['maximum'] = total
            
            # 获取第三列的列名
            third_column = result_df.columns[2]
            
            # 遍历所有记录
            for idx, row in result_df.iterrows():
                if self.is_closing:
                    break
                    
                code = row['代码']
                link = row['链接']
                
                # 检查第三列是否有内容
                if pd.isna(row[third_column]):
                    try:
                        # 爬取数据
                        page_data = fetch_card_page(link)
                        if not self.is_closing:
                            self.log(f"成功爬取第 {idx+1}/{total} 个页面 - 代码: {code}, 链接: {link}")
                        
                        # 更新当前行的数据
                        for key, value in page_data.items():
                            if key in result_df.columns:
                                result_df.at[idx, key] = value
                        
                        # 保存到文件
                        result_df.to_excel('card_info.xlsx', index=False)
                        if not self.is_closing:
                            self.log(f"已更新第 {idx+1}/{total} 条数据")
                    except Exception as e:
                        if not self.is_closing:
                            self.log(f"爬取页面失败 {link}: {str(e)}")
                else:
                    if not self.is_closing:
                        self.log(f"跳过第 {idx+1}/{total} 个页面 - 代码: {code} (已有数据)")
                
                if not self.is_closing:
                    self.progress['value'] = idx + 1
                    self.root.update()
                
            if not self.is_closing:
                self.log("所有页面爬取完成！")
        except Exception as e:
            if not self.is_closing:
                self.log(f"爬取过程中出错: {str(e)}")
        finally:
            if not self.is_closing:
                self.btn_fetch_pages.config(state='normal')
                self.progress['value'] = 0

if __name__ == "__main__":
    root = tk.Tk()
    app = SpiderGUI(root)
    root.mainloop() 