# gui_pyside.py
"""
安利日本产品自动化系统 - PySide6 GUI
"""
import sys
import asyncio
import threading
from pathlib import Path
from datetime import datetime
from io import StringIO
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QRadioButton, QCheckBox, QButtonGroup,
    QGroupBox, QTextEdit, QStatusBar, QProgressBar, QFileDialog,
    QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QTextCursor

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from core.browser import BrowserManager
from core.login import LoginManager
from core.product_processor import ProductProcessor
from utils.progress_manager import ProgressManager


class WorkerThread(QThread):
    """工作线程"""
    
    log_signal = Signal(str, str)  # 消息, 级别
    status_signal = Signal(str, str)  # 文本, 颜色
    finished_signal = Signal()
    error_signal = Signal(str)
    
    def __init__(self, mode, headless, config, progress, export_summary=True, export_single_word=True):
        super().__init__()
        self.mode = mode
        self.headless = headless
        self.config = config
        self.progress = progress
        self.export_summary = export_summary
        self.export_single_word = export_single_word
        self._is_running = True
    
    def stop(self):
        self._is_running = False
    
    def run(self):
        """在工作线程中运行任务"""
        # 🔑 重定向 stdout/stderr 到 GUI
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        class GUIPrint:
            def __init__(self, log_signal):
                self.log_signal = log_signal
                self.buffer = ""
            
            def write(self, text):
                if text:
                    self.buffer += text
                    if '\n' in self.buffer:
                        lines = self.buffer.split('\n')
                        for line in lines[:-1]:
                            if line.strip():
                                self.log_signal.emit(line, "INFO")
                        self.buffer = lines[-1]
            
            def flush(self):
                if self.buffer.strip():
                    self.log_signal.emit(self.buffer.strip(), "INFO")
                    self.buffer = ""
        
        sys.stdout = GUIPrint(self.log_signal)
        sys.stderr = GUIPrint(self.log_signal)
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._run_task())
        except Exception as e:
            self.error_signal.emit(str(e))
            import traceback
            traceback.print_exc()
        finally:
            # 恢复原始 stdout
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.finished_signal.emit()
    
    async def _run_task(self):
        """执行异步任务"""
        config = self.config
        
        try:
            # export 模式不需要浏览器
            if self.mode == "export":
                self.log_signal.emit("📄 仅导出模式，不需要浏览器", "INFO")
                processor = ProductProcessor(
                    browser=None,
                    config=config,
                    progress=self.progress,
                    logger=None
                )
                # 🔑 临时覆盖导出配置
                processor.config.ENABLE_SUMMARY_EXPORT = self.export_summary
                processor.config.ENABLE_SINGLE_WORD = self.export_single_word
                await processor.process_all()
                self.log_signal.emit("✅ 文档导出完成！", "SUCCESS")
                return
            
            # 其他模式需要浏览器
            self.log_signal.emit("🚀 启动浏览器...", "INFO")
            
            # 临时修改配置
            original_headless = config.HEADLESS
            config.HEADLESS = self.headless
            
            browser = await BrowserManager(config).start()
            
            # 检查网站状态
            self.log_signal.emit("🔍 检查网站状态...", "INFO")
            await browser.page.goto(config.LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # 检测维护
            if await self._check_maintenance(browser):
                self.log_signal.emit("❌ 网站正在维护，请稍后再试", "ERROR")
                return
            
            # 登录
            self.log_signal.emit("🔐 登录...", "INFO")
            login_manager = LoginManager(browser.page, config)
            if not await login_manager.login():
                self.log_signal.emit("❌ 登录失败", "ERROR")
                return
            
            self.log_signal.emit("✅ 登录成功", "SUCCESS")
            
            # 创建处理器
            processor = ProductProcessor(
                browser=browser,
                config=config,
                progress=self.progress,
                logger=None
            )
            
            # 🔑 应用导出配置
            processor.config.ENABLE_SUMMARY_EXPORT = self.export_summary
            processor.config.ENABLE_SINGLE_WORD = self.export_single_word
            
            # 执行任务
            if self.mode == "fetch":
                self.log_signal.emit("🌐 获取产品列表...", "INFO")
                # fetch 模式需要添加方法
                self.log_signal.emit("⚠️ fetch 模式暂未实现", "WARNING")
            elif self.mode == "scan":
                self.log_signal.emit("📋 仅扫描模式...", "INFO")
                await processor.scan_all_products()
                await processor.verify_no_sharebar()
                self.log_signal.emit("✅ 扫描完成！", "SUCCESS")
            else:
                await processor.process_all()
            
            self.log_signal.emit("✅ 所有任务完成！", "SUCCESS")
            
        except Exception as e:
            self.log_signal.emit(f"❌ 执行出错: {e}", "ERROR")
            import traceback
            traceback.print_exc()
        finally:
            if 'browser' in locals() and browser:
                await browser.close()
    
    async def _check_maintenance(self, browser) -> bool:
        """检查网站是否维护"""
        try:
            await browser.page.wait_for_load_state("domcontentloaded", timeout=10000)
            await asyncio.sleep(1)
            
            page_text = await browser.page.inner_text('body')
            self.log_signal.emit(f"📄 页面内容预览: {page_text[:200]}...", "INFO")
            
            maintenance_keywords = [
                'メンテナンス', 'ご利用いただけません', '作業のため',
                'しばらくお待ちください', 'システムメンテナンス', 'メンテナンス中',
                '一時休止', '時間帯はご利用', '作業を実施', 'メンテナンス作業',
            ]
            
            for keyword in maintenance_keywords:
                if keyword in page_text:
                    self.log_signal.emit(f"⚠️ 网站维护中: {keyword}", "WARNING")
                    return True
            
            return False
            
        except Exception as e:
            self.log_signal.emit(f"⚠️ 检查维护状态失败: {e}", "WARNING")
            return False


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config = Config.ensure_directories()
        self.progress = ProgressManager(self.config.PRODUCTS_DIR)
        self.worker = None
        
        self.setWindowTitle("安利日本产品自动化系统")
        self.setMinimumSize(850, 700)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #1a237e;
            }
            QPushButton {
                background-color: #1a237e;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #283593;
            }
            QPushButton:disabled {
                background-color: #9e9e9e;
            }
            QPushButton#stopBtn {
                background-color: #c62828;
            }
            QPushButton#stopBtn:hover {
                background-color: #b71c1c;
            }
            QPushButton#openBtn {
                background-color: #2e7d32;
            }
            QPushButton#openBtn:hover {
                background-color: #1b5e20;
            }
            QPushButton#resetBtn {
                background-color: #e65100;
            }
            QPushButton#resetBtn:hover {
                background-color: #bf360c;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, monospace;
                font-size: 11px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QRadioButton {
                padding: 4px 12px;
            }
            QRadioButton:checked {
                color: #1a237e;
                font-weight: bold;
            }
            QCheckBox {
                padding: 4px 8px;
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 12, 16, 12)
        
        # ---- 标题 ----
        title_label = QLabel("🛍️ 安利日本产品自动化系统")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #1a237e; padding: 4px 0;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # ---- 模式选择 ----
        mode_group = QGroupBox("运行模式")
        mode_layout = QHBoxLayout(mode_group)
        
        self.mode_buttons = {}
        modes = [
            ("完整流程", "full"),
            ("仅扫描", "scan"),
            ("仅导出文档", "export"),
            ("获取产品列表", "fetch"),
        ]
        
        for text, value in modes:
            radio = QRadioButton(text)
            radio.setProperty("mode", value)
            mode_layout.addWidget(radio)
            self.mode_buttons[value] = radio
        
        mode_layout.addStretch()
        main_layout.addWidget(mode_group)
        self.mode_buttons["full"].setChecked(True)
        
        # ---- 选项 ----
        option_layout = QVBoxLayout()
        
        # 第一行：无头模式
        row1 = QHBoxLayout()
        self.headless_check = QCheckBox("无头模式 (不显示浏览器窗口)")
        row1.addWidget(self.headless_check)
        row1.addStretch()
        option_layout.addLayout(row1)
        
        # 第二行：导出选项
        row2 = QHBoxLayout()
        self.export_summary_check = QCheckBox("📄 导出汇总文档 (HTML/PDF/Word)")
        self.export_summary_check.setChecked(True)
        row2.addWidget(self.export_summary_check)
        
        self.export_single_check = QCheckBox("📄 导出单个产品 Word 文档")
        self.export_single_check.setChecked(True)
        row2.addWidget(self.export_single_check)
        row2.addStretch()
        option_layout.addLayout(row2)
        
        main_layout.addLayout(option_layout)
        
        # ---- 日志区域 ----
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_group)
        
        # ---- 进度条 ----
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 4px;
                height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1a237e;
                border-radius: 4px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # ---- 按钮 ----
        btn_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("▶ 运行")
        self.run_btn.clicked.connect(self._run)
        btn_layout.addWidget(self.run_btn)
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        btn_layout.addWidget(self.stop_btn)
        
        btn_layout.addSpacing(20)
        
        self.open_btn = QPushButton("📁 打开输出目录")
        self.open_btn.setObjectName("openBtn")
        self.open_btn.clicked.connect(self._open_output_dir)
        btn_layout.addWidget(self.open_btn)
        
        self.reset_btn = QPushButton("🗑️ 重置进度")
        self.reset_btn.setObjectName("resetBtn")
        self.reset_btn.clicked.connect(self._reset_progress)
        btn_layout.addWidget(self.reset_btn)
        
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)
        
        # ---- 状态栏 ----
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("● 空闲")
        self.status_bar.setStyleSheet("color: #4caf50; padding: 4px 8px;")
    
    def _log(self, message, level="INFO"):
        """添加日志到 GUI（支持彩色）"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # 颜色映射
        color_map = {
            "INFO": "#4fc3f7",
            "WARNING": "#ffb74d", 
            "ERROR": "#ef5350",
            "SUCCESS": "#66bb6a",
        }
        color = color_map.get(level, "#d4d4d4")
        
        # 使用 HTML 格式添加彩色日志
        html = f'<span style="color:#888888;">[{timestamp}] </span>'
        html += f'<span style="color:{color};">{message}</span><br>'
        
        self.log_text.append(html)
        
        # 滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        
        # 处理进度条
        if "处理进度:" in message:
            try:
                import re
                match = re.search(r'(\d+)/(\d+)', message)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    self.progress_bar.setVisible(True)
                    self.progress_bar.setRange(0, total)
                    self.progress_bar.setValue(current)
                    self.progress_bar.setFormat(f"{current}/{total}")
            except:
                pass
        
        if "完成" in message and "✅" in message:
            QTimer.singleShot(2000, self._hide_progress)
    
    def _hide_progress(self):
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
    
    def _set_status(self, text, color="green"):
        """设置状态栏"""
        color_map = {"green": "#4caf50", "orange": "#ff9800", "red": "#c62828"}
        self.status_bar.showMessage(f"● {text}")
        self.status_bar.setStyleSheet(f"color: {color_map.get(color, color)}; padding: 4px 8px;")
    
    def _update_buttons(self, running):
        """更新按钮状态"""
        self.run_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.open_btn.setEnabled(not running)
        self.reset_btn.setEnabled(not running)
        
        if running:
            self._set_status("运行中...", "orange")
        else:
            self._set_status("空闲", "green")
    
    def _run(self):
        """运行任务"""
        if self.worker and self.worker.isRunning():
            return
        
        self.log_text.clear()
        self.progress_bar.setVisible(False)
        
        mode = None
        for value, btn in self.mode_buttons.items():
            if btn.isChecked():
                mode = value
                break
        
        headless = self.headless_check.isChecked()
        export_summary = self.export_summary_check.isChecked()
        export_single = self.export_single_check.isChecked()
        
        self._log(f"🚀 启动任务 (模式: {mode}, 无头: {headless})", "SUCCESS")
        self._log(f"📄 导出汇总: {export_summary}, 导出单产品Word: {export_single}", "INFO")
        
        self._update_buttons(True)
        
        # 创建工作线程
        self.worker = WorkerThread(
            mode, headless, self.config, self.progress,
            export_summary, export_single
        )
        self.worker.log_signal.connect(self._log)
        self.worker.status_signal.connect(self._set_status)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()
    
    def _stop(self):
        """停止任务"""
        if self.worker and self.worker.isRunning():
            self._log("⏹ 正在停止...", "WARNING")
            self.worker.stop()
            self.worker.quit()
            self.worker.wait(3000)
            self._on_finished()
    
    def _on_finished(self):
        """任务完成"""
        self._update_buttons(False)
        self._log("⏹ 任务已停止", "WARNING")
    
    def _on_error(self, error):
        """错误处理"""
        self._log(f"❌ {error}", "ERROR")
        self._update_buttons(False)
    
    def _open_output_dir(self):
        """打开输出目录"""
        import os
        path = str(self.config.EXPORTS_DIR)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        os.startfile(path)
    
    def _reset_progress(self):
        """重置进度"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置所有进度吗？\n这将清除已处理产品的记录。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.progress.reset()
            qr_file = self.config.PRODUCTS_DIR / "qr_progress.json"
            if qr_file.exists():
                qr_file.unlink()
            self._log("🔄 进度已重置", "WARNING")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()