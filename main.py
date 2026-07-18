# main.py
"""
安利日本产品自动化系统 - 主入口
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from core.browser import BrowserManager
from core.login import LoginManager
from core.product_processor import ProductProcessor
from utils.progress_manager import ProgressManager
from utils.logger import setup_logger


class AmwayAutomation:
    """主程序"""
    
    def __init__(self, headless: bool = None):
        self.config = Config.ensure_directories()
        self.logger = setup_logger(self.config.LOGS_DIR / "app.log")
        self.browser = None
        # 🔑 使用 PRODUCTS_DIR
        self.progress = ProgressManager(self.config.PRODUCTS_DIR)
        self.headless = headless if headless is not None else self.config.HEADLESS
    
    # main.py

    async def run(self, mode: str = "full"):
        """
        执行主流程
        
        Args:
            mode: 运行模式
                - "full": 完整流程（需要浏览器）
                - "export": 仅导出文档（不需要浏览器）
                - "scan": 仅扫描（需要浏览器）
                - "fetch": 从网站获取产品列表（需要浏览器）
        """
        self.logger.info("=" * 60)
        self.logger.info(f"安利产品自动化系统 - 模式: {mode}")
        self.logger.info("=" * 60)
        
        try:
            # 🔑 export 模式不需要浏览器
            if mode == "export":
                self.logger.info("📄 仅导出模式，不需要浏览器")
                processor = ProductProcessor(
                    browser=None,
                    config=self.config,
                    progress=self.progress,
                    logger=self.logger
                )
                await processor.export_html_and_pdf()
                self.logger.info("✅ 文档导出完成！")
                return
            
            # 🔑 其他模式需要浏览器
            self.logger.info("🚀 启动浏览器...")
            self.browser = await BrowserManager(self.config).start()
            
            self.logger.info("🔐 登录...")
            login_manager = LoginManager(self.browser.page, self.config)
            if not await login_manager.login():
                self.logger.error("❌ 登录失败")
                return
            
            processor = ProductProcessor(
                browser=self.browser,
                config=self.config,
                progress=self.progress,
                logger=self.logger
            )
            
            if mode == "fetch":
                # 🔑 仅获取产品列表
                self.logger.info("🌐 获取产品列表...")
                await processor.fetch_all_product_urls()
                self.logger.info("✅ 产品列表获取完成！")
                
            elif mode == "scan":
                # 仅扫描模式
                self.logger.info("📋 仅扫描模式...")
                await processor.scan_all_products()
                await processor.verify_no_sharebar()
                self.logger.info("✅ 扫描完成！")
                
            else:
                # full 模式：完整流程
                await processor.process_all()
            
            self.logger.info("=" * 60)
            self.logger.info("✅ 所有任务完成！")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"❌ 执行出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.browser:
                await self.browser.close()  

# main.py - 修改 argparse 部分
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="安利日本产品自动化系统")
    parser.add_argument(
        "--mode", 
        choices=["full", "scan", "export", "fetch"],
        default="full",
        help="运行模式: full=完整流程, scan=仅扫描, export=仅导出文档, fetch=获取产品列表"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式（不显示浏览器）"
    )
    
    args = parser.parse_args()
    
    app = AmwayAutomation(headless=args.headless)
    asyncio.run(app.run(mode=args.mode))

if __name__ == "__main__":
    main()