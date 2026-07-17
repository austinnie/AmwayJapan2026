"""
产品处理器 - 核心逻辑（完整版）
支持：图片获取、Sharebar、分类列表、二次确认、HTML导出、PDF导出
"""
import asyncio
from pathlib import Path
from typing import List, Dict, Optional

from config import Config
from core.browser import BrowserManager
from handlers.sharebar_handler import SharebarHandler
from handlers.image_handler import ImageHandler
from handlers.qr_handler import QRHandler
from handlers.html_handler import HTMLHandler
from handlers.pdf_handler import PDFHandler
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
        self.html_handler = HTMLHandler()
        self.pdf_handler = PDFHandler()
        
        # 分类列表
        self.with_sharebar: List[Dict] = []      # 有 Sharebar
        self.without_sharebar: List[Dict] = []   # 无 Sharebar
        self.all_products: List[Dict] = []       # 所有产品
    
    def log(self, msg: str, level: str = "info"):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(msg)
    
    # ============================================================
    # 第一步：扫描所有产品
    # ============================================================
    async def scan_all_products(self):
        """第一步：扫描所有产品，获取图片和 Sharebar"""
        self.log("\n" + "=" * 60)
        self.log("📋 第一步：扫描所有产品")
        self.log("=" * 60)
        
        product_urls = self.file_utils.load_product_list("list-all.txt")
        if not product_urls:
            self.log("❌ 未找到产品列表", "error")
            return
        
        self.log(f"📊 共 {len(product_urls)} 个产品待扫描")
        
        total = len(product_urls)
        
        for i, url in enumerate(product_urls):
            product_id = self.file_utils.extract_product_id(url)
            
            if self.progress.is_processed(product_id):
                self.log(f"⏭️ [{i+1}/{total}] 产品 {product_id} 已处理，跳过")
                continue
            
            self.log(f"\n📦 [{i+1}/{total}] 扫描产品: {product_id}")
            
            result = await self._scan_single_product(url, product_id)
            
            if result:
                self.progress.mark_processed(product_id)
                self.progress.save()
            
            await asyncio.sleep(self.config.REQUEST_DELAY)
        
        # 保存分类列表
        self._save_category_lists()
        
        self.log("\n" + "=" * 60)
        self.log(f"📊 第一步完成:")
        self.log(f"   有 Sharebar: {len(self.with_sharebar)} 个")
        self.log(f"   无 Sharebar: {len(self.without_sharebar)} 个")
        self.log("=" * 60)
    
    async def _scan_single_product(self, url: str, product_id: str) -> bool:
        """扫描单个产品"""
        page = await self.browser.context.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # 1. 获取产品名称
            product_name = await self._extract_product_name(page)
            
            # 2. 获取产品图片
            category_dirs = self.file_utils.get_category_dir("all")
            image_dir = category_dirs / "product_images"
            image_dir.mkdir(parents=True, exist_ok=True)
            
            image_path = await self.image_handler.capture_product_image(
                page, product_id, image_dir
            )
            
            # 3. 尝试获取 Sharebar
            sharebar = await self.sharebar_handler.get_sharebar_link(url, retry=1)
            
            # 4. 记录结果
            product_info = {
                'product_id': product_id,
                'url': url,
                'name': product_name,
                'image_path': str(image_path) if image_path else None,
                'sharebar': sharebar,
                'has_sharebar': sharebar is not None,
                'status': 'scanned'
            }
            
            self.all_products.append(product_info)
            
            if sharebar:
                self.with_sharebar.append(product_info)
                self.log(f"   ✅ 有 Sharebar: {sharebar}")
            else:
                self.without_sharebar.append(product_info)
                self.log(f"   ⚠️ 无 Sharebar")
            
            return True
            
        except Exception as e:
            self.log(f"   ❌ 扫描失败: {e}", "error")
            return False
        finally:
            await page.close()
    
    async def _extract_product_name(self, page) -> str:
        """提取产品名称"""
        try:
            # 方法1: 通过常见选择器
            selectors = [
                'h1.product-title',
                'h1.product-name',
                '.product-title',
                '.product-name',
                'h1'
            ]
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    name = await element.inner_text()
                    if name and len(name) > 2:
                        return name.strip()
            
            # 方法2: 从页面标题提取
            title = await page.title()
            if title:
                # 移除网站名称后缀
                for suffix in ['| アムウェイ', '| Amway', ' - Amway']:
                    if suffix in title:
                        title = title.split(suffix)[0]
                if title and len(title) > 2:
                    return title.strip()
            
            # 方法3: 从 meta 标签提取
            meta_title = await page.get_attribute('meta[property="og:title"]', 'content')
            if meta_title and len(meta_title) > 2:
                return meta_title.strip()
            
        except Exception as e:
            self.log(f"   ⚠️ 提取名称异常: {e}")
        
        return "未知产品"
    
    # ============================================================
    # 第二步：二次确认
    # ============================================================
    async def verify_no_sharebar(self):
        """第二步：对无 Sharebar 的产品二次确认"""
        if not self.without_sharebar:
            self.log("\n✅ 所有产品都有 Sharebar，无需二次确认")
            return
        
        self.log("\n" + "=" * 60)
        self.log("🔍 第二步：二次确认无 Sharebar 的产品")
        self.log("=" * 60)
        self.log(f"📊 共 {len(self.without_sharebar)} 个产品需要确认")
        
        confirmed_with_sharebar = []
        confirmed_without_sharebar = []
        
        for i, product in enumerate(self.without_sharebar):
            product_id = product['product_id']
            url = product['url']
            
            self.log(f"\n📦 [{i+1}/{len(self.without_sharebar)}] 确认产品: {product_id}")
            
            # 二次确认（重试 3 次）
            result = await self.sharebar_handler.verify_no_sharebar(url, max_retry=3)
            
            if result['has_sharebar']:
                product['sharebar'] = result['sharebar']
                product['has_sharebar'] = True
                confirmed_with_sharebar.append(product)
                self.log(f"   ✅ 确认有 Sharebar: {result['sharebar']} (尝试 {result['attempts']} 次)")
            else:
                confirmed_without_sharebar.append(product)
                self.log(f"   ❌ 确认无 Sharebar (尝试 {result['attempts']} 次)")
        
        # 更新列表
        self.with_sharebar.extend(confirmed_with_sharebar)
        self.without_sharebar = confirmed_without_sharebar
        
        # 重新保存列表
        self._save_category_lists()
        
        self.log("\n" + "=" * 60)
        self.log(f"📊 二次确认完成:")
        self.log(f"   新增有 Sharebar: {len(confirmed_with_sharebar)} 个")
        self.log(f"   确认无 Sharebar: {len(confirmed_without_sharebar)} 个")
        self.log("=" * 60)
    
    # ============================================================
    # 第三步：生成二维码并合并图片
    # ============================================================
    async def generate_qr_and_merge(self):
        """第三步：生成二维码并合并图片"""
        self.log("\n" + "=" * 60)
        self.log("📱 第三步：生成二维码并合并图片")
        self.log("=" * 60)
        
        all_products = self.with_sharebar + self.without_sharebar
        self.log(f"📊 共 {len(all_products)} 个产品需要处理")
        
        category_dirs = self.file_utils.get_category_dir("all")
        qr_dir = category_dirs / "qr_codes"
        qr_dir.mkdir(parents=True, exist_ok=True)
        merged_dir = category_dirs / "merged_images"
        merged_dir.mkdir(parents=True, exist_ok=True)
        
        for i, product in enumerate(all_products):
            product_id = product['product_id']
            image_path = product.get('image_path')
            
            if not image_path or not Path(image_path).exists():
                self.log(f"⚠️ [{i+1}/{len(all_products)}] 产品 {product_id} 无图片，跳过")
                continue
            
            self.log(f"\n📦 [{i+1}/{len(all_products)}] 处理产品: {product_id}")
            
            # 🔑 决定使用哪个 URL 生成二维码
            if product['has_sharebar'] and product.get('sharebar'):
                qr_url = product['sharebar']
                qr_type = "Sharebar"
            else:
                qr_url = product['url']
                qr_type = "产品URL"
            
            self.log(f"   📱 使用 {qr_type} 生成二维码")
            
            # 生成二维码
            qr_path = qr_dir / f"{product_id}_qr.png"
            qr_result = self.qr_handler.generate_qr(qr_url, qr_path)
            
            if qr_result:
                # 合并图片
                merged_path = merged_dir / f"{product_id}_merged.png"
                merge_result = self.qr_handler.merge_with_product(
                    Path(image_path), qr_path, merged_path
                )
                if merge_result:
                    product['merged_path'] = str(merge_result)
                    self.log(f"   ✅ 合并完成")
            else:
                self.log(f"   ❌ 二维码生成失败")
            
            await asyncio.sleep(0.5)
        
        self.log("\n✅ 二维码生成和图片合并完成")
    
    # ============================================================
    # 第四步：导出 HTML 和 PDF
    # ============================================================
    async def export_html_and_pdf(self):
        """第四步：导出 HTML 和 PDF 文档"""
        self.log("\n" + "=" * 60)
        self.log("📄 第四步：导出 HTML 和 PDF")
        self.log("=" * 60)
        
        all_products = self.with_sharebar + self.without_sharebar
        if not all_products:
            self.log("⚠️ 没有产品数据可导出")
            return
        
        # 确保输出目录存在
        self.config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # 准备图片复制（HTML需要引用图片）
        self._prepare_images_for_export(all_products)
        
        # 1. 导出全产品
        self.log("📄 导出全产品目录...")
        base_name = "安利日本产品目录"
        html_path = self.config.OUTPUT_DIR / f"{base_name}.html"
        pdf_path = self.config.OUTPUT_DIR / f"{base_name}.pdf"
        
        if self.html_handler.export_products(all_products, html_path, "全产品"):
            self.log(f"   ✅ HTML: {html_path}")
        else:
            self.log(f"   ❌ HTML 导出失败")
        
        if self.pdf_handler.export_products(all_products, pdf_path, "全产品"):
            self.log(f"   ✅ PDF: {pdf_path}")
        else:
            self.log(f"   ⚠️ PDF 导出失败（请安装 weasyprint 或 wkhtmltopdf）")
        
        # 2. 导出有 Sharebar 产品
        if self.with_sharebar:
            self.log("📄 导出有 Sharebar 产品目录...")
            base_name = "有Sharebar产品"
            html_path = self.config.OUTPUT_DIR / f"{base_name}.html"
            pdf_path = self.config.OUTPUT_DIR / f"{base_name}.pdf"
            
            self.html_handler.export_products(self.with_sharebar, html_path, "有Sharebar产品")
            self.pdf_handler.export_products(self.with_sharebar, pdf_path, "有Sharebar产品")
        
        # 3. 导出无 Sharebar 产品
        if self.without_sharebar:
            self.log("📄 导出无 Sharebar 产品目录...")
            base_name = "无Sharebar产品"
            html_path = self.config.OUTPUT_DIR / f"{base_name}.html"
            pdf_path = self.config.OUTPUT_DIR / f"{base_name}.pdf"
            
            self.html_handler.export_products(self.without_sharebar, html_path, "无Sharebar产品")
            self.pdf_handler.export_products(self.without_sharebar, pdf_path, "无Sharebar产品")
        
        self.log("\n" + "=" * 60)
        self.log("✅ 文档导出完成!")
        self.log(f"📁 输出目录: {self.config.OUTPUT_DIR}")
        self.log("=" * 60)
    
    def _prepare_images_for_export(self, products: List[Dict]):
        """准备导出用的图片（复制到输出目录）"""
        output_images_dir = self.config.OUTPUT_DIR / "images"
        output_images_dir.mkdir(parents=True, exist_ok=True)
        
        for product in products:
            # 复制合并图片
            merged_path = product.get('merged_path')
            if merged_path and Path(merged_path).exists():
                dest = output_images_dir / Path(merged_path).name
                if not dest.exists():
                    try:
                        import shutil
                        shutil.copy2(merged_path, dest)
                    except:
                        pass
            
            # 复制原始图片（如果没有合并图片）
            elif product.get('image_path') and Path(product['image_path']).exists():
                dest = output_images_dir / Path(product['image_path']).name
                if not dest.exists():
                    try:
                        import shutil
                        shutil.copy2(product['image_path'], dest)
                    except:
                        pass
    
    # ============================================================
    # 保存分类列表
    # ============================================================
    def _save_category_lists(self):
        """保存分类列表"""
        # 有 Sharebar
        with open(self.config.PRODUCTS_DIR / "list-withsharebar.txt", 'w', encoding='utf-8') as f:
            for p in self.with_sharebar:
                f.write(f"{p['url']}\n")
        
        # 无 Sharebar
        with open(self.config.PRODUCTS_DIR / "list-withoutsharebar.txt", 'w', encoding='utf-8') as f:
            for p in self.without_sharebar:
                f.write(f"{p['url']}\n")
        
        self.log(f"✅ 已保存分类列表:")
        self.log(f"   有 Sharebar: list-withsharebar.txt ({len(self.with_sharebar)} 个)")
        self.log(f"   无 Sharebar: list-withoutsharebar.txt ({len(self.without_sharebar)} 个)")
    
    # ============================================================
    # 主入口
    # ============================================================
    async def process_all(self):
        """执行完整流程"""
        # 第一步：扫描
        await self.scan_all_products()
        
        # 第二步：二次确认
        await self.verify_no_sharebar()
        
        # 第三步：生成二维码并合并
        await self.generate_qr_and_merge()
        
        # 第四步：导出 HTML 和 PDF
        await self.export_html_and_pdf()
        
        self.log("\n" + "=" * 60)
        self.log("✅ 所有处理完成！")
        self.log(f"   有 Sharebar: {len(self.with_sharebar)} 个")
        self.log(f"   无 Sharebar: {len(self.without_sharebar)} 个")
        self.log(f"📁 输出目录: {self.config.OUTPUT_DIR}")
        self.log("=" * 60)