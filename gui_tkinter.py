# gui_tkinter.py
"""
安利日本产品自动化系统 - GUI界面
"""
import asyncio
import threading
import sys
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from core.browser import BrowserManager
from core.login import LoginManager
from core.product_processor import ProductProcessor
from utils.progress_manager import ProgressManager
from utils.logger import setup_logger


class RedirectLogger:
    """将日志重定向到GUI文本框"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""
    
    def write(self, message):
        if message:
            self.buffer += message
            if '\n' in self.buffer:
                self.text_widget.insert(tk.END, self.buffer)
                self.text_widget.see(tk.END)
                self.text_widget.update_idletasks()
                self.buffer = ""
    
    def flush(self):
        if self.buffer:
            self.text_widget.insert(tk.END, self.buffer)
            self.text_widget.see(tk.END)
            self.text_widget.update_idletasks()
            self.buffer = ""


class AmwayGUI:
    """主界面"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("安利日本产品自动化系统")
        self.root.geometry("800x650")
        self.root.minsize(700, 550)
        
        # 设置图标
        try:
            self.root.iconbitmap(default='icon.ico')
        except:
            pass
        
        # 配置
        self.config = Config.ensure_directories()
        self.logger = None
        self.browser = None
        self.progress = ProgressManager(self.config.PRODUCTS_DIR)
        self.running = False
        self.loop = None
        
        # 创建界面
        self._create_widgets()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self):
        """创建界面组件"""
        
        # ===== 标题 =====
        title_frame = tk.Frame(self.root, bg='#1a237e', height=60)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🛍️ 安利日本产品自动化系统",
            font=('Microsoft YaHei', 18, 'bold'),
            fg='white',
            bg='#1a237e'
        )
        title_label.pack(pady=12)
        
        # ===== 主框架 =====
        main_frame = tk.Frame(self.root, padx=15, pady=10)
        main_frame.pack(fill='both', expand=True)
        
        # ---- 模式选择 ----
        mode_frame = tk.LabelFrame(main_frame, text="运行模式", font=('Microsoft YaHei', 11), padx=10, pady=8)
        mode_frame.pack(fill='x', pady=(0, 10))
        
        self.mode_var = tk.StringVar(value="full")
        
        modes = [
            ("完整流程", "full"),
            ("仅扫描", "scan"),
            ("仅导出文档", "export"),
            ("获取产品列表", "fetch"),
        ]
        
        for text, value in modes:
            tk.Radiobutton(
                mode_frame,
                text=text,
                variable=self.mode_var,
                value=value,
                font=('Microsoft YaHei', 10)
            ).pack(side='left', padx=15)
        
        # ---- 选项 ----
        option_frame = tk.Frame(main_frame)
        option_frame.pack(fill='x', pady=(0, 10))
        
        # 第一行：无头模式
        self.headless_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            option_frame,
            text="无头模式 (不显示浏览器窗口)",
            variable=self.headless_var,
            font=('Microsoft YaHei', 10)
        ).pack(side='left', padx=(0, 20))
        
        # 第二行：导出选项（新的一行）
        export_frame = tk.Frame(main_frame)
        export_frame.pack(fill='x', pady=(0, 10))
        
        self.export_summary_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            export_frame,
            text="📄 导出汇总文档 (HTML/PDF/Word)",
            variable=self.export_summary_var,
            font=('Microsoft YaHei', 10)
        ).pack(side='left', padx=(0, 20))
        
        self.export_single_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            export_frame,
            text="📄 导出单个产品 Word 文档",
            variable=self.export_single_var,
            font=('Microsoft YaHei', 10)
        ).pack(side='left')
        
        # ---- 日志区域 ----
        log_frame = tk.LabelFrame(main_frame, text="运行日志", font=('Microsoft YaHei', 11), padx=10, pady=8)
        log_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=('Consolas', 10),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white',
            wrap=tk.WORD,
            height=15
        )
        self.log_text.pack(fill='both', expand=True)
        
        # 配置日志标签颜色
        self.log_text.tag_config('INFO', foreground='#4fc3f7')
        self.log_text.tag_config('WARNING', foreground='#ffb74d')
        self.log_text.tag_config('ERROR', foreground='#ef5350')
        self.log_text.tag_config('SUCCESS', foreground='#66bb6a')
        
        # 重定向输出
        sys.stdout = RedirectLogger(self.log_text)
        
        # ---- 按钮 ----
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=5)
        
        self.run_btn = tk.Button(
            btn_frame,
            text="▶ 运行",
            font=('Microsoft YaHei', 11, 'bold'),
            bg='#1a237e',
            fg='white',
            padx=30,
            pady=8,
            cursor='hand2',
            command=self._run
        )
        self.run_btn.pack(side='left', padx=(0, 10))
        
        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹ 停止",
            font=('Microsoft YaHei', 11, 'bold'),
            bg='#c62828',
            fg='white',
            padx=30,
            pady=8,
            cursor='hand2',
            command=self._stop,
            state='disabled'
        )
        self.stop_btn.pack(side='left', padx=(0, 10))
        
        tk.Button(
            btn_frame,
            text="📁 打开输出目录",
            font=('Microsoft YaHei', 10),
            padx=15,
            pady=8,
            cursor='hand2',
            command=self._open_output_dir
        ).pack(side='left', padx=(0, 10))
        
        tk.Button(
            btn_frame,
            text="🗑️ 重置进度",
            font=('Microsoft YaHei', 10),
            padx=15,
            pady=8,
            cursor='hand2',
            command=self._reset_progress
        ).pack(side='left')
        
        # ---- 状态栏 ----
        status_frame = tk.Frame(self.root, bg='#f0f0f0', height=30)
        status_frame.pack(fill='x', side='bottom')
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            status_frame,
            text="● 空闲",
            font=('Microsoft YaHei', 10),
            bg='#f0f0f0',
            anchor='w',
            padx=10
        )
        self.status_label.pack(fill='x')
    
    def _log(self, message, level='INFO'):
        """添加日志到文本框"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if not message:
            return
        
        lines = message.split('\n')
        for i, line in enumerate(lines):
            if i == 0:
                self.log_text.insert(tk.END, f"[{timestamp}] ", 'INFO')
                self.log_text.insert(tk.END, f"{line}\n", level)
            else:
                self.log_text.insert(tk.END, f"           {line}\n", level)
        
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()
    
    def _set_status(self, text, color='#4caf50'):
        """设置状态栏"""
        self.status_label.config(text=f"● {text}", fg=color)
    
    def _update_buttons(self, running):
        """更新按钮状态"""
        self.running = running
        if running:
            self.run_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self._set_status('运行中...', '#ff9800')
        else:
            self.run_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            self._set_status('空闲', '#4caf50')
    
    def _run(self):
        """运行任务"""
        if self.running:
            return
        
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        
        mode = self.mode_var.get()
        headless = self.headless_var.get()
        export_summary = self.export_summary_var.get()
        export_single = self.export_single_var.get()
        
        self._log(f"🚀 启动任务 (模式: {mode}, 无头: {headless})", 'SUCCESS')
        self._log(f"📄 导出汇总: {export_summary}, 导出单产品Word: {export_single}", 'INFO')
        
        self._update_buttons(True)
        
        # 在新线程中运行
        thread = threading.Thread(
            target=self._run_async,
            args=(mode, headless, export_summary, export_single),
            daemon=True
        )
        thread.start()
    
    def _run_async(self, mode, headless, export_summary, export_single):
        """在新线程中运行异步任务"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.loop = loop
            
            loop.run_until_complete(
                self._run_task(mode, headless, export_summary, export_single)
            )
            
        except Exception as e:
            self._log(f"❌ 执行出错: {e}", 'ERROR')
            import traceback
            traceback.print_exc()
        finally:
            if self.loop:
                self.loop.close()
                self.loop = None
            self.root.after(0, lambda: self._update_buttons(False))
    
    async def _run_task(self, mode, headless, export_summary, export_single):
        """执行异步任务"""
        config = self.config
        
        try:
            # export 模式不需要浏览器
            if mode == "export":
                self._log("📄 仅导出模式，不需要浏览器", 'INFO')
                processor = ProductProcessor(
                    browser=None,
                    config=config,
                    progress=self.progress,
                    logger=None
                )
                processor.config.ENABLE_SUMMARY_EXPORT = export_summary
                processor.config.ENABLE_SINGLE_WORD = export_single
                await processor.process_all()
                self._log("✅ 文档导出完成！", 'SUCCESS')
                return
            
            # 其他模式需要浏览器
            self._log("🚀 启动浏览器...", 'INFO')
            
            original_headless = config.HEADLESS
            config.HEADLESS = headless
            
            browser = await BrowserManager(config).start()
            self.browser = browser
            
            # 检查网站状态
            self._log("🔍 检查网站状态...", 'INFO')
            await browser.page.goto(config.LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # 检测维护
            if await self._check_maintenance(browser):
                self._log("❌ 网站正在维护，请稍后再试", 'ERROR')
                return
            
            # 登录
            self._log("🔐 登录...", 'INFO')
            login_manager = LoginManager(browser.page, config)
            if not await login_manager.login():
                self._log("❌ 登录失败", 'ERROR')
                return
            
            self._log("✅ 登录成功", 'SUCCESS')
            
            # 创建处理器
            processor = ProductProcessor(
                browser=browser,
                config=config,
                progress=self.progress,
                logger=None
            )
            processor.config.ENABLE_SUMMARY_EXPORT = export_summary
            processor.config.ENABLE_SINGLE_WORD = export_single
            
            # 执行任务
            if mode == "fetch":
                self._log("🌐 获取产品列表...", 'INFO')
                self._log("⚠️ fetch 模式暂未实现", 'WARNING')
            elif mode == "scan":
                self._log("📋 仅扫描模式...", 'INFO')
                await processor.scan_all_products()
                await processor.verify_no_sharebar()
                self._log("✅ 扫描完成！", 'SUCCESS')
            else:
                await processor.process_all()
            
            self._log("✅ 所有任务完成！", 'SUCCESS')
            
        except Exception as e:
            self._log(f"❌ 执行出错: {e}", 'ERROR')
            import traceback
            traceback.print_exc()
        finally:
            if self.browser:
                await self.browser.close()
                self.browser = None
    
    async def _check_maintenance(self, browser) -> bool:
        """检查网站是否维护"""
        try:
            await browser.page.wait_for_load_state("domcontentloaded", timeout=10000)
            await asyncio.sleep(1)
            
            page_text = await browser.page.inner_text('body')
            self._log(f"📄 页面内容预览: {page_text[:200]}...", 'INFO')
            
            maintenance_keywords = [
                'メンテナンス', 'ご利用いただけません', '作業のため',
                'しばらくお待ちください', 'システムメンテナンス', 'メンテナンス中',
                '一時休止', '時間帯はご利用', '作業を実施', 'メンテナンス作業',
            ]
            
            for keyword in maintenance_keywords:
                if keyword in page_text:
                    self._log(f"⚠️ 网站维护中: {keyword}", 'WARNING')
                    return True
            
            title = await browser.page.title()
            if title:
                for keyword in ['メンテナンス', 'maintenance']:
                    if keyword.lower() in title.lower():
                        self._log(f"⚠️ 网站维护中: {title}", 'WARNING')
                        return True
            
            return False
            
        except Exception as e:
            self._log(f"⚠️ 检查维护状态失败: {e}", 'WARNING')
            return False
    
    def _stop(self):
        """停止任务"""
        self._log("⏹ 正在停止...", 'WARNING')
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        self._update_buttons(False)
        self._log("⏹ 已停止", 'WARNING')
    
    def _open_output_dir(self):
        """打开输出目录"""
        import os
        path = str(self.config.EXPORTS_DIR)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        os.startfile(path)
    
    def _reset_progress(self):
        """重置进度"""
        if messagebox.askyesno("确认", "确定要重置所有进度吗？\n这将清除已处理产品的记录。"):
            self.progress.reset()
            qr_file = self.config.PRODUCTS_DIR / "qr_progress.json"
            if qr_file.exists():
                qr_file.unlink()
            self._log("🔄 进度已重置", 'WARNING')
    
    def _on_closing(self):
        """关闭窗口"""
        if self.running:
            if not messagebox.askyesno("确认", "任务正在运行，确定要退出吗？"):
                return
        self.root.destroy()
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()


if __name__ == "__main__":
    app = AmwayGUI()
    app.run()