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
    
    async def _check_maintenance(self) -> bool:
        """检查网站是否处于维护状态"""
        try:
            await self.browser.page.wait_for_load_state("domcontentloaded", timeout=10000)
            await asyncio.sleep(1)
            
            page_text = await self.browser.page.inner_text('body')
            self.logger.info(f"📄 当前页面内容预览: {page_text[:200]}...")
            
            maintenance_keywords = [
                'メンテナンス', 'ご利用いただけません', '作業のため',
                'しばらくお待ちください', 'システムメンテナンス', 'メンテナンス中',
                '一時休止', '時間帯はご利用', '作業を実施', 'メンテナンス作業',
                '利用できません', 'ただいま混雑', 'アクセス集中',
            ]
            
            for keyword in maintenance_keywords:
                if keyword in page_text:
                    self.logger.warning(f"⚠️ 网站维护中: {keyword}")
                    return True
            
            title = await self.browser.page.title()
            if title:
                for keyword in ['メンテナンス', 'maintenance']:
                    if keyword.lower() in title.lower():
                        self.logger.warning(f"⚠️ 网站维护中: {title}")
                        return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ 检查维护状态失败: {e}")
            return False

    async def run(self, mode: str = None):
        """
        执行主流程
        
        Args:
            mode: 运行模式，如果不指定则使用 config 中的配置
        """
        # 🔑 从配置读取默认值
        if mode is None:
            mode = self.config.RUN_MODE
        
        enable_retry = self.config.ENABLE_RETRY
        
        self.logger.info("=" * 60)
        self.logger.info(f"安利产品自动化系统 - 模式: {mode}")
        self.logger.info(f"二次确认: {'启用' if enable_retry else '禁用'}")
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
            
            self.logger.info("🔍 检查网站状态...")
            await self.browser.page.goto(self.config.LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            if await self._check_maintenance():
                self.logger.error("❌ 网站正在维护，请稍后再试")
                return
            
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
                self.logger.info("🌐 获取产品列表...")
                await processor.fetch_all_product_urls()
                self.logger.info("✅ 产品列表获取完成！")
                
            elif mode == "scan":
                self.logger.info("📋 仅扫描模式...")
                await processor.scan_all_products()
                if enable_retry:
                    self.logger.info("🔄 执行二次确认...")
                    await processor.verify_no_sharebar()
                else:
                    self.logger.info("⏭️ 跳过二次确认")
                self.logger.info("✅ 扫描完成！")
                
            else:  # full
                await processor.process_all(
                    skip_scan=False,
                    enable_retry=enable_retry
                )
            
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
    import argparse
    
    parser = argparse.ArgumentParser(description="安利日本产品自动化系统")
    parser.add_argument(
        "--mode", 
        choices=["full", "scan", "export", "fetch"],
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