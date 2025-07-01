import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from ws_fetcher import get_card_links, fetch_all_pages, save_to_excel, download_card_images
import threading
import pandas as pd
import os
import sys
import re
import atexit
import psutil
import signal

class WS_SpiderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WS卡片爬虫")
        self.root.geometry("600x400")
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 创建输入框和标签
        ttk.Label(main_frame, text="总页数:").grid(row=0, column=0, sticky=tk.W)
        self.pages_entry = ttk.Entry(main_frame, width=10)
        self.pages_entry.grid(row=0, column=1, sticky=tk.W)
        self.pages_entry.insert(0, "1")
        
        # 创建按钮
        self.get_links_btn = ttk.Button(main_frame, text="开始获取", command=self.start_get_links)
        self.get_links_btn.grid(row=0, column=2, padx=5)
        
        # 添加下载图片按钮
        self.download_images_btn = ttk.Button(main_frame, text="下载图片", command=self.start_download_images)
        self.download_images_btn.grid(row=0, column=3, padx=5)
        
        # 创建进度条
        self.progress = ttk.Progressbar(main_frame, length=400, mode='determinate')
        self.progress.grid(row=1, column=0, columnspan=4, pady=10)
        
        # 创建状态标签
        self.status_label = ttk.Label(main_frame, text="就绪")
        self.status_label.grid(row=2, column=0, columnspan=4)
        
        # 创建日志文本框
        self.log_text = scrolledtext.ScrolledText(main_frame, width=60, height=20)
        self.log_text.grid(row=3, column=0, columnspan=4, pady=10)
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始化变量
        self.is_running = False
        self.should_stop = False
        self.thread = None
        self.driver_pid = None
        
        # 注册退出处理函数
        atexit.register(self.cleanup)
    
    def log(self, message):
        """显示日志消息"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
    
    def start_get_links(self):
        """开始获取卡片数据"""
        if self.is_running:
            messagebox.showwarning("警告", "任务正在运行中")
            return
        
        # 获取总页数
        try:
            total_pages = int(self.pages_entry.get())
            if total_pages <= 0:
                messagebox.showerror("错误", "请输入大于0的数字")
                return
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return
        
        # 重置停止标志
        self.should_stop = False
        
        # 禁用按钮
        self.get_links_btn.state(['disabled'])
        self.download_images_btn.state(['disabled'])
        self.is_running = True
        
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        
        # 开始新线程
        self.thread = threading.Thread(target=self.fetch_pages_thread, args=(total_pages,))
        self.thread.daemon = True  # 设置为守护线程
        self.thread.start()
    
    def fetch_pages_thread(self, total_pages):
        """在线程中获取卡片数据"""
        try:
            self.log(f"开始获取 {total_pages} 页的卡片数据...")
            
            # 获取所有页面的数据
            all_cards, driver_pid = fetch_all_pages(total_pages, self.should_stop)
            
            # 保存进程ID
            if driver_pid:
                self.driver_pid = driver_pid
            
            if self.should_stop:
                self.log("任务已终止")
                return
                
            if all_cards:
                # 保存到Excel
                save_to_excel(all_cards)
                self.log(f"成功获取 {len(all_cards)} 张卡片数据")
            else:
                self.log("未获取到任何卡片数据")
            
        except Exception as e:
            self.log(f"获取数据时出错: {str(e)}")
        finally:
            # 恢复按钮状态
            self.root.after(0, self.reset_buttons)
    
    def start_download_images(self):
        """开始下载图片"""
        if self.is_running:
            messagebox.showwarning("警告", "任务正在运行中")
            return
        
        # 检查Excel文件是否存在
        if not os.path.exists("ws_cards.xlsx"):
            messagebox.showerror("错误", "请先获取卡片数据！")
            return
        
        # 重置停止标志
        self.should_stop = False
        
        # 禁用按钮
        self.download_images_btn.state(['disabled'])
        self.is_running = True
        
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        
        # 开始新线程
        self.thread = threading.Thread(target=self.download_images_thread)
        self.thread.daemon = True
        self.thread.start()
    
    def download_images_thread(self):
        """在线程中下载图片"""
        try:
            self.log("开始下载卡片图片...")
            
            # 下载图片
            downloaded, total = download_card_images()
            
            if self.should_stop:
                self.log("任务已终止")
                return
            
            self.log(f"下载完成！成功下载: {downloaded}，总计: {total}")
            
        except Exception as e:
            self.log(f"下载图片时出错: {str(e)}")
        finally:
            # 恢复按钮状态
            self.root.after(0, self.reset_buttons)
    
    def reset_buttons(self):
        """重置按钮状态"""
        self.get_links_btn.state(['!disabled'])
        self.download_images_btn.state(['!disabled'])
        self.is_running = False
        self.should_stop = False
    
    def kill_process_tree(self, pid):
        """强制结束进程及其子进程"""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # 先结束子进程
            for child in children:
                try:
                    child.kill()
                except:
                    pass
            
            # 再结束父进程
            try:
                parent.kill()
            except:
                pass
                
        except:
            pass
    
    def cleanup(self):
        """清理资源"""
        self.should_stop = True
        
        # 强制结束浏览器进程
        if self.driver_pid:
            self.kill_process_tree(self.driver_pid)
        
        # 等待线程结束
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
    
    def on_closing(self):
        """关闭窗口时的处理"""
        if self.is_running:
            if messagebox.askokcancel("确认", "任务正在运行中，确定要退出吗？"):
                self.should_stop = True
                self.cleanup()
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = WS_SpiderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 