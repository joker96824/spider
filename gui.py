import tkinter as tk
from tkinter import ttk, scrolledtext
from fetcher import get_card_links, fetch_card_page, cleanup, download_card_images, convert_to_sql
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
        
        # 添加下载图片按钮
        self.btn_download_images = ttk.Button(root, text="下载卡片图片", command=self.start_download_images)
        self.btn_download_images.pack(pady=10)
        
        # 添加导出SQL按钮
        self.btn_export_sql = ttk.Button(root, text="导出SQL文件", command=self.start_export_sql)
        self.btn_export_sql.pack(pady=10)
        
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
        thread.daemon = True
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
            self.log("请先获取卡片链接！")
            return
            
        self.btn_fetch_pages.config(state='disabled')
        self.log("开始爬取卡片页面...")
        thread = threading.Thread(target=self.fetch_pages_thread)
        thread.daemon = True
        thread.start()
        
    def fetch_pages_thread(self):
        """爬取页面的线程函数"""
        try:
            # 读取xlsx文件
            df = pd.read_excel('card_links.xlsx')
            card_links = df['link'].tolist()
            total = len(card_links)
            self.progress['maximum'] = total
            
            # 如果勾选了跳过选项，读取已存在的card_info.xlsx
            existing_codes = set()
            if self.skip_existing.get() and os.path.exists('card_info.xlsx'):
                try:
                    existing_df = pd.read_excel('card_info.xlsx')
                    existing_codes = set(existing_df['代码'].tolist())
                    self.log(f"找到 {len(existing_codes)} 条已爬取记录")
                except Exception as e:
                    self.log(f"读取已存在文件时出错: {str(e)}")
            
            all_card_data = []
            for idx, link in enumerate(card_links, 1):
                if self.is_closing:
                    break
                    
                code = df.iloc[idx-1]['code']
                
                # 如果勾选了跳过选项且该卡片已爬取，则跳过
                if self.skip_existing.get() and code in existing_codes:
                    if not self.is_closing:
                        self.log(f"跳过已爬取的第 {idx}/{total} 个页面 - 代码: {code}")
                    continue
                    
                try:
                    page_data = fetch_card_page(link)
                    if not self.is_closing:
                        self.log(f"成功爬取第 {idx}/{total} 个页面 - 代码: {code}, 链接: {link}")
                    
                    # 准备当前卡片的数据
                    card_info = {
                        '代码': code,
                        '链接': link,
                        **page_data  # 将page_data中的所有信息添加到字典中
                    }
                    all_card_data.append(card_info)
                    
                except Exception as e:
                    if not self.is_closing:
                        self.log(f"爬取页面失败 {link}: {str(e)}")
                    # 即使爬取失败也添加空记录
                    card_info = {
                        '代码': code,
                        '链接': link
                    }
                    all_card_data.append(card_info)
                    
                if not self.is_closing:
                    self.progress['value'] = idx
                    self.root.update()
            
            # 保存所有卡片信息到xlsx文件
            if all_card_data:
                result_df = pd.DataFrame(all_card_data)
                result_df.to_excel('card_info.xlsx', index=False)
                if not self.is_closing:
                    self.log(f"所有卡片信息已保存到 card_info.xlsx，共 {len(all_card_data)} 条记录")
                
            if not self.is_closing:
                self.log("所有页面爬取完成！")
        except Exception as e:
            if not self.is_closing:
                self.log(f"爬取过程中出错: {str(e)}")
        finally:
            if not self.is_closing:
                self.btn_fetch_pages.config(state='normal')
                self.progress['value'] = 0

    def start_download_images(self):
        """启动下载图片的线程"""
        if self.is_closing:
            return
            
        if not os.path.exists('card_info.xlsx'):
            self.log("请先爬取卡片数据！")
            return
            
        self.btn_download_images.config(state='disabled')
        self.log("开始下载卡片图片...")
        thread = threading.Thread(target=self.download_images_thread)
        thread.daemon = True
        thread.start()
        
    def download_images_thread(self):
        """下载图片的线程函数"""
        try:
            # 读取卡片数据
            df = pd.read_excel('card_info.xlsx')
            total = len(df)
            self.progress['maximum'] = total
            
            # 下载图片
            downloaded, total = download_card_images(df)
            
            if not self.is_closing:
                self.log(f"图片下载完成！成功下载 {downloaded}/{total} 张图片")
        except Exception as e:
            if not self.is_closing:
                self.log(f"下载图片时出错: {str(e)}")
        finally:
            if not self.is_closing:
                self.btn_download_images.config(state='normal')
                self.progress['value'] = 0

    def start_export_sql(self):
        """启动导出SQL的线程"""
        if self.is_closing:
            return
            
        if not os.path.exists('card_info.xlsx'):
            self.log("请先爬取卡片数据！")
            return
            
        self.btn_export_sql.config(state='disabled')
        self.log("开始导出SQL文件...")
        thread = threading.Thread(target=self.export_sql_thread)
        thread.daemon = True
        thread.start()
        
    def export_sql_thread(self):
        """导出SQL的线程函数"""
        try:
            # 读取卡片数据
            df = pd.read_excel('card_info.xlsx')
            
            # 导出SQL文件
            output_file = convert_to_sql(df)
            
            if not self.is_closing:
                self.log(f"SQL文件导出完成！文件保存在: {output_file}")
        except Exception as e:
            if not self.is_closing:
                self.log(f"导出SQL文件时出错: {str(e)}")
        finally:
            if not self.is_closing:
                self.btn_export_sql.config(state='normal')

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

if __name__ == "__main__":
    root = tk.Tk()
    app = SpiderGUI(root)
    root.mainloop() 