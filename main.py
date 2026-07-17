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
    
    def __init__(self):
        self.config = Config.ensure_directories()
        self.logger = setup_logger(self.config.LOGS_DIR / "app.log")
        self.browser = None
        self.progress = ProgressManager(self.config.OUTPUT_DIR)
    
    async def run(self):
        """执行主流程"""
        self.logger.info("=" * 60)
        self.logger.info("安利产品自动化系统 - Playwright 版")
        self.logger.info("=" * 60)
        
        try:
            # 1. 启动浏览器
            self.logger.info("🚀 启动浏览器...")
            self.browser = await BrowserManager(self.config).start()
            
            # 2. 登录
            self.logger.info("🔐 登录...")
            login_manager = LoginManager(self.browser.page, self.config)
            if not await login_manager.login():
                self.logger.error("❌ 登录失败")
                return
            
            # 3. 创建产品处理器
            processor = ProductProcessor(
                browser=self.browser,
                config=self.config,
                progress=self.progress,
                logger=self.logger
            )
            
            # 4. 执行处理
            await processor.process_all()
            
            # 5. 生成报告
            self.logger.info("📊 生成报告...")
            # TODO: 调用报告生成器
            
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


def main():
    app = AmwayAutomation()
    asyncio.run(app.run())


if __name__ == "__main__":
    main()