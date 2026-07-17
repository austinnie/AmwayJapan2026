"""
产品处理器 - 核心逻辑
"""
import asyncio
from pathlib import Path

from config import Config
from core.browser import BrowserManager
from handlers.sharebar_handler import SharebarHandler
from handlers.image_handler import ImageHandler
from handlers.qr_handler import QRHandler
from utils.file_utils import FileUtils
from utils.progress_manager import ProgressManager


class ProductProcessor:
    """产品处理器"""
    
    def __init__(self, browser: BrowserManager, config: Config, 
                 progress: ProgressManager, logger=None):
        self.browser = browser
        self.config = config
        self.progress = progress
        self.logger = logger
        
        self.file_utils = FileUtils(config.PRODUCTS_DIR)
        self.sharebar_handler = SharebarHandler(browser.context)
        self.image_handler = ImageHandler()
        self.qr_handler = QRHandler()
    
    def log(self, msg: str, level: str = "info"):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(msg)
    
    async def process_all(self):
        """处理所有产品"""
        product_urls = self.file_utils.load_product_list("list-all.txt")
        if not product_urls:
            self.log("❌ 未找到产品列表", "error")
            return
        
        self.log(f"📋 共 {len(product_urls)} 个产品待处理")
        
        total = len(product_urls)
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        for i, url in enumerate(product_urls):
            product_id = self.file_utils.extract_product_id(url)
            
            if self.progress.is_processed(product_id):
                self.log(f"⏭️ [{i+1}/{total}] 产品 {product_id} 已处理，跳过")
                skip_count += 1
                continue
            
            self.log(f"\n📦 [{i+1}/{total}] 处理产品: {product_id}")
            
            result = await self._process_product(url, product_id)
            
            if result:
                success_count += 1
                self.progress.mark_processed(product_id)
                self.progress.save()
            else:
                fail_count += 1
            
            await asyncio.sleep(self.config.REQUEST_DELAY)
        
        self.log("\n" + "=" * 50)
        self.log(f"📊 处理完成统计:")
        self.log(f"   总产品: {total}")
        self.log(f"   成功: {success_count}")
        self.log(f"   失败: {fail_count}")
        self.log(f"   跳过: {skip_count}")
        self.log("=" * 50)
    
    async def _process_product(self, url: str, product_id: str) -> bool:
        """处理单个产品"""
        try:
            # 🔽 创建新页面（用于截图）
            page = await self.browser.context.new_page()
            
            try:
                # 1. 打开产品页面
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                
                # 2. 🔽 截取产品图片
                # 获取分类目录
                category_dirs = self.file_utils.get_category_dir("all")
                image_dir = category_dirs / "product_images"
                image_dir.mkdir(parents=True, exist_ok=True)
                
                image_path = await self.image_handler.capture_product_image(
                    page, product_id, image_dir
                )
                
                # 3. 获取 Sharebar 链接（使用主页面）
                sharebar = await self.sharebar_handler.get_sharebar_link(url)
                
                # 4. 🔽 如果有 Sharebar，生成二维码并合并
                if sharebar and image_path:
                    # 生成二维码
                    qr_dir = category_dirs / "qr_codes"
                    qr_dir.mkdir(parents=True, exist_ok=True)
                    qr_path = qr_dir / f"{product_id}_qr.png"
                    
                    qr_result = self.qr_handler.generate_qr(sharebar, qr_path)
                    
                    if qr_result:
                        # 合并图片
                        merged_dir = category_dirs / "merged_images"
                        merged_dir.mkdir(parents=True, exist_ok=True)
                        merged_path = merged_dir / f"{product_id}_merged.png"
                        
                        self.qr_handler.merge_with_product(image_path, qr_path, merged_path)
                
                if sharebar:
                    self.log(f"   ✅ Sharebar: {sharebar}")
                    return True
                else:
                    self.log(f"   ⚠️ 未获取到 Sharebar")
                    return False
                
            finally:
                await page.close()
            
        except Exception as e:
            self.log(f"   ❌ 处理失败: {e}", "error")
            return False