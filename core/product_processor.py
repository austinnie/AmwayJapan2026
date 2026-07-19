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
        
        if browser is not None and hasattr(browser, 'context'):
            self.sharebar_handler = SharebarHandler(browser.context)
        else:
            self.sharebar_handler = None
        
        self.image_handler = ImageHandler()
        self.qr_handler = QRHandler()
        self.html_handler = HTMLHandler()
        self.pdf_handler = PDFHandler()
        
        self.with_sharebar: List[Dict] = []
        self.without_sharebar: List[Dict] = []
        self.all_products: List[Dict] = []
    
    def log(self, msg: str, level: str = "info"):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(msg)
    
    # ============================================================
    # 第一步：扫描所有产品
    # ============================================================
    async def scan_all_products(self):
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
            
            product_name = await self._extract_product_name(page, product_id)
            
            category_dirs = self.file_utils.get_category_dir("all")
            image_dir = category_dirs / "product_images"
            image_dir.mkdir(parents=True, exist_ok=True)
            
            image_path = await self.image_handler.capture_product_image(
                page, product_id, image_dir
            )
            
            # 🔑 使用配置中的重试次数
            sharebar = await self.sharebar_handler.get_sharebar_link(
                url, 
                retry=self.config.SHAREBAR_RETRY_COUNT
            )
            
            self._save_product_name(product_id, product_name)
            
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
                self._append_to_category_list(product_id, url, "withsharebar")
                self._save_sharebar_mapping(product_id, sharebar)
                self.log(f"   ✅ 有 Sharebar: {sharebar}")
            else:
                self.without_sharebar.append(product_info)
                self._append_to_category_list(product_id, url, "withoutsharebar")
                self.log(f"   ⚠️ 无 Sharebar")
            
            return True
            
        except Exception as e:
            self.log(f"   ❌ 扫描失败: {e}", "error")
            return False
        finally:
            await page.close()
    
    def _save_product_name(self, product_id: str, product_name: str):
        import json
        name_file = self.config.PRODUCTS_DIR / "product_names.json"
        
        data = {}
        if name_file.exists():
            try:
                with open(name_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                pass
        
        data[product_id] = product_name
        
        with open(name_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_product_name(self, product_id: str) -> str:
        import json
        name_file = self.config.PRODUCTS_DIR / "product_names.json"
        if name_file.exists():
            try:
                with open(name_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get(product_id, f"产品 {product_id}")
            except:
                pass
        return f"产品 {product_id}"
    
    def _save_sharebar_mapping(self, product_id: str, sharebar: str):
        import json
        mapping_file = self.config.PRODUCTS_DIR / "sharebar_mapping.json"
        
        data = {}
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                pass
        
        data[product_id] = sharebar
        
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_sharebar_from_mapping(self, product_id: str) -> str:
        import json
        mapping_file = self.config.PRODUCTS_DIR / "sharebar_mapping.json"
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get(product_id)
            except:
                pass
        return None
    
    def _append_to_category_list(self, product_id: str, url: str, category: str):
        filename = f"list-{category}.txt"
        file_path = self.config.PRODUCTS_DIR / filename
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f"{url}\n")
    
    async def _extract_product_name(self, page, product_id: str = "") -> str:
        try:
            title = await page.title()
            if title:
                suffixes = [
                    ' | アムウェイ', ' | Amway', ' - Amway',
                    '｜アムウェイ', '：Amway', '| amwaylive',
                    '｜amwaylive', ' - amwaylive',
                ]
                
                product_name = title
                for suffix in suffixes:
                    if suffix in product_name:
                        product_name = product_name.split(suffix)[0].strip()
                        break
                
                if '：' in product_name:
                    product_name = product_name.split('：')[0].strip()
                if '|' in product_name:
                    product_name = product_name.split('|')[0].strip()
                if ' - ' in product_name:
                    product_name = product_name.split(' - ')[0].strip()
                
                if product_name and len(product_name) > 2:
                    product_name = product_name.strip('()（）')
                    self.log(f"   ✅ 从标题提取: {product_name[:50]}...")
                    return product_name
            
            meta_title = await page.get_attribute('meta[property="og:title"]', 'content')
            if meta_title:
                product_name = meta_title.strip()
                for suffix in [' | アムウェイ', ' | Amway', ' - Amway', '｜アムウェイ', '：Amway']:
                    if suffix in product_name:
                        product_name = product_name.split(suffix)[0].strip()
                        break
                if '：' in product_name:
                    product_name = product_name.split('：')[0].strip()
                if '|' in product_name:
                    product_name = product_name.split('|')[0].strip()
                product_name = product_name.strip('()（）')
                if product_name and len(product_name) > 2:
                    self.log(f"   ✅ 从meta提取: {product_name[:50]}...")
                    return product_name
            
            h1_elements = await page.query_selector_all('h1')
            for h1 in h1_elements:
                text = await h1.inner_text()
                text = text.strip()
                if text and len(text) > 2 and len(text) < 100:
                    skip_words = ['おすすめ', 'キャンペーン', 'ログイン', 'メニュー', '検索', 'カート']
                    if not any(skip in text for skip in skip_words):
                        self.log(f"   ✅ 从h1提取: {text[:50]}...")
                        return text
            
        except Exception as e:
            self.log(f"   ⚠️ 提取名称异常: {e}")
        
        return f"产品 {product_id}" if product_id else "未知产品"
    
    # ============================================================
    # 第二步：二次确认（支持断点续传）
    # ============================================================
    async def verify_no_sharebar(self):
        if not self.without_sharebar:
            self.log("\n✅ 所有产品都有 Sharebar，无需二次确认")
            return
        
        self.log("\n" + "=" * 60)
        self.log("🔍 第二步：二次确认无 Sharebar 的产品")
        self.log("=" * 60)
        self.log(f"📊 共 {len(self.without_sharebar)} 个产品需要确认")
        
        # 🔑 加载二次确认进度
        verified_progress = self._load_verified_progress()
        
        confirmed_with_sharebar = []
        confirmed_without_sharebar = []
        
        for i, product in enumerate(self.without_sharebar):
            product_id = product['product_id']
            url = product['url']
            
            # 🔑 跳过已确认的
            if product_id in verified_progress:
                # 从已确认列表中恢复状态
                if product.get('has_sharebar'):
                    confirmed_with_sharebar.append(product)
                else:
                    confirmed_without_sharebar.append(product)
                self.log(f"⏭️ [{i+1}/{len(self.without_sharebar)}] 产品 {product_id} 已确认，跳过")
                continue
            
            self.log(f"\n📦 [{i+1}/{len(self.without_sharebar)}] 确认产品: {product_id}")
            
            # 🔑 使用配置中的重试次数
            result = await self.sharebar_handler.verify_no_sharebar(
                url, 
                max_retry=self.config.RETRY_COUNT
            )
            if result['has_sharebar']:
                product['sharebar'] = result['sharebar']
                product['has_sharebar'] = True
                confirmed_with_sharebar.append(product)
                self.log(f"   ✅ 确认有 Sharebar: {result['sharebar']}")
            else:
                confirmed_without_sharebar.append(product)
                self.log(f"   ❌ 确认无 Sharebar")
            
            # 🔑 每确认一个立即保存进度
            self._save_verified_progress(product_id, result['has_sharebar'])
        
        self.with_sharebar.extend(confirmed_with_sharebar)
        self.without_sharebar = confirmed_without_sharebar
        self._save_category_lists()
        
        self.log("\n" + "=" * 60)
        self.log(f"📊 二次确认完成:")
        self.log(f"   新增有 Sharebar: {len(confirmed_with_sharebar)} 个")
        self.log(f"   确认无 Sharebar: {len(confirmed_without_sharebar)} 个")
        self.log("=" * 60)


    # ============================================================
    # 二次确认进度管理
    # ============================================================
    def _load_verified_progress(self) -> dict:
        """加载二次确认进度"""
        progress_file = self.config.PRODUCTS_DIR / "verified_progress.json"
        if progress_file.exists():
            try:
                import json
                with open(progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_verified_progress(self, product_id: str, has_sharebar: bool):
        """保存单个产品二次确认进度"""
        import json
        progress_file = self.config.PRODUCTS_DIR / "verified_progress.json"
        
        data = self._load_verified_progress()
        data[product_id] = has_sharebar
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
    # ============================================================
    # 第三步：生成二维码并合并图片
    # ============================================================
    async def generate_qr_and_merge(self):
        with_sharebar_urls = self._load_urls_from_file("list-withsharebar.txt")
        without_sharebar_urls = self._load_urls_from_file("list-withoutsharebar.txt")
        
        all_urls = with_sharebar_urls + without_sharebar_urls
        self.log(f"\n📱 第三步：生成二维码并合并图片")
        self.log(f"📊 有Sharebar: {len(with_sharebar_urls)} 个")
        self.log(f"📊 无Sharebar: {len(without_sharebar_urls)} 个")
        self.log(f"📊 共 {len(all_urls)} 个产品需要处理")
        
        category_dirs = self.file_utils.get_category_dir("all")
        qr_dir = category_dirs / "qr_codes"
        qr_dir.mkdir(parents=True, exist_ok=True)
        merged_dir = category_dirs / "merged_images"
        merged_dir.mkdir(parents=True, exist_ok=True)
        
        processed_qr = self._load_qr_progress()
        has_sharebar_set = set(with_sharebar_urls)
        
        for i, url in enumerate(all_urls):
            product_id = self.file_utils.extract_product_id(url)
            
            if product_id in processed_qr:
                self.log(f"⏭️ [{i+1}/{len(all_urls)}] 产品 {product_id} 已处理，跳过")
                continue
            
            image_path = category_dirs / "merged_images" / f"{product_id}.png"
            if not image_path.exists():
                image_path = category_dirs / "product_images" / f"{product_id}.png"
                if not image_path.exists():
                    self.log(f"⚠️ [{i+1}/{len(all_urls)}] 产品 {product_id} 无图片，跳过")
                    continue
            
            self.log(f"\n📦 [{i+1}/{len(all_urls)}] 处理产品: {product_id}")
            
            if url in has_sharebar_set:
                sharebar = self._get_sharebar_from_mapping(product_id)
                if not sharebar:
                    sharebar = await self.sharebar_handler.get_sharebar_link(url, retry=2)
                    if sharebar:
                        self._save_sharebar_mapping(product_id, sharebar)
                
                qr_url = sharebar if sharebar else url
                qr_type = "Sharebar" if sharebar else "产品URL(降级)"
            else:
                qr_url = url
                qr_type = "产品URL"
            
            self.log(f"   📱 使用 {qr_type} 生成二维码")
            
            qr_path = qr_dir / f"{product_id}_qr.png"
            qr_result = self.qr_handler.generate_qr(qr_url, qr_path)
            
            if qr_result:
                merged_path = merged_dir / f"{product_id}_merged.png"
                merge_result = self.qr_handler.merge_with_image(
                    image_path, qr_path, merged_path
                )
                if merge_result:
                    self.log(f"   ✅ 合并完成")
                    self._save_qr_progress(product_id)
                else:
                    self.log(f"   ❌ 合并失败")
            else:
                self.log(f"   ❌ 二维码生成失败")
            
            await asyncio.sleep(0.5)
        
        self.log("\n✅ 二维码生成和图片合并完成")
    
    def _load_urls_from_file(self, filename: str) -> List[str]:
        file_path = self.config.PRODUCTS_DIR / filename
        urls = []
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and 'amwaylive.com' in line:
                        urls.append(line)
        return urls
    
    def _load_qr_progress(self) -> set:
        progress_file = self.config.PRODUCTS_DIR / "qr_progress.json"
        if progress_file.exists():
            try:
                import json
                with open(progress_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except:
                pass
        return set()
    
    def _save_qr_progress(self, product_id: str):
        import json
        progress_file = self.config.PRODUCTS_DIR / "qr_progress.json"
        processed = self._load_qr_progress()
        processed.add(product_id)
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(list(processed), f, ensure_ascii=False, indent=2)
    
    # ============================================================
    # 第四步：导出 HTML 和 PDF
    # ============================================================
    def _get_sharebar_from_mapping(self, product_id: str) -> str:
        import json
        mapping_file = self.config.PRODUCTS_DIR / "sharebar_mapping.json"
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get(product_id)
            except:
                pass
        return None
    
    async def export_html_and_pdf(self):
        self.log("\n" + "=" * 60)
        self.log("📄 第四步：导出 HTML、PDF 和 Word")
        self.log("=" * 60)
        
        with_sharebar_urls = self._load_urls_from_file("list-withsharebar.txt")
        without_sharebar_urls = self._load_urls_from_file("list-withoutsharebar.txt")
        
        if not with_sharebar_urls and not without_sharebar_urls:
            self.log("⚠️ 没有产品数据可导出")
            return
        
        all_products = []
        with_sharebar_products = []
        without_sharebar_products = []
        
        category_dirs = self.file_utils.get_category_dir("all")
        image_dir = category_dirs / "product_images"
        merged_dir = category_dirs / "merged_images"
        
        for url in with_sharebar_urls:
            product_id = self.file_utils.extract_product_id(url)
            sharebar = self._get_sharebar_from_mapping(product_id)
            product_name = self._get_product_name(product_id)
            
            image_path = image_dir / f"{product_id}.png"
            merged_path = merged_dir / f"{product_id}_merged.png"
            
            product_info = {
                'product_id': product_id,
                'url': url,
                'name': product_name,
                'image_path': str(image_path) if image_path.exists() else None,
                'sharebar': sharebar,
                'has_sharebar': True,
                'merged_path': str(merged_path) if merged_path.exists() else None
            }
            all_products.append(product_info)
            with_sharebar_products.append(product_info)
        
        for url in without_sharebar_urls:
            product_id = self.file_utils.extract_product_id(url)
            product_name = self._get_product_name(product_id)
            
            image_path = image_dir / f"{product_id}.png"
            merged_path = merged_dir / f"{product_id}_merged.png"
            
            product_info = {
                'product_id': product_id,
                'url': url,
                'name': product_name,
                'image_path': str(image_path) if image_path.exists() else None,
                'sharebar': None,
                'has_sharebar': False,
                'merged_path': str(merged_path) if merged_path.exists() else None
            }
            all_products.append(product_info)
            without_sharebar_products.append(product_info)
        
        self.log(f"📊 有Sharebar: {len(with_sharebar_products)} 个")
        self.log(f"📊 无Sharebar: {len(without_sharebar_products)} 个")
        self.log(f"📊 共 {len(all_products)} 个产品")
        
        # 使用 exports 目录
        exports_dir = self.config.EXPORTS_DIR
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        from handlers.word_handler import WordHandler
        word_handler = WordHandler()
        
        base_name = "安利日本产品目录"
        html_path = exports_dir / f"{base_name}.html"
        pdf_path = exports_dir / f"{base_name}.pdf"
        word_path = exports_dir / f"{base_name}.docx"
        
        self.html_handler.export_products(all_products, html_path, "全产品")
        await self.pdf_handler.export_products(all_products, pdf_path, "全产品")
        word_handler.export_products(all_products, word_path, "全产品")
        
        if with_sharebar_products:
            self.log("📄 导出有 Sharebar 产品目录...")
            base_name = "有Sharebar产品"
            html_path = exports_dir / f"{base_name}.html"
            pdf_path = exports_dir / f"{base_name}.pdf"
            word_path = exports_dir / f"{base_name}.docx"
            
            self.html_handler.export_products(with_sharebar_products, html_path, "有Sharebar产品")
            await self.pdf_handler.export_products(with_sharebar_products, pdf_path, "有Sharebar产品")
            word_handler.export_products(with_sharebar_products, word_path, "有Sharebar产品")
        
        if without_sharebar_products:
            self.log("📄 导出无 Sharebar 产品目录...")
            base_name = "无Sharebar产品"
            html_path = exports_dir / f"{base_name}.html"
            pdf_path = exports_dir / f"{base_name}.pdf"
            word_path = exports_dir / f"{base_name}.docx"
            
            self.html_handler.export_products(without_sharebar_products, html_path, "无Sharebar产品")
            await self.pdf_handler.export_products(without_sharebar_products, pdf_path, "无Sharebar产品")
            word_handler.export_products(without_sharebar_products, word_path, "无Sharebar产品")
        
        self.log("\n" + "=" * 60)
        self.log("✅ 文档导出完成!")
        self.log(f"📁 输出目录: {exports_dir}")
        self.log("=" * 60)
    
    # ============================================================
    # 保存分类列表
    # ============================================================
    def _save_category_lists(self):
        with open(self.config.PRODUCTS_DIR / "list-withsharebar.txt", 'w', encoding='utf-8') as f:
            for p in self.with_sharebar:
                f.write(f"{p['url']}\n")
        
        with open(self.config.PRODUCTS_DIR / "list-withoutsharebar.txt", 'w', encoding='utf-8') as f:
            for p in self.without_sharebar:
                f.write(f"{p['url']}\n")
        
        self.log(f"✅ 已保存分类列表:")
        self.log(f"   有 Sharebar: list-withsharebar.txt ({len(self.with_sharebar)} 个)")
        self.log(f"   无 Sharebar: list-withoutsharebar.txt ({len(self.without_sharebar)} 个)")
    
    # ============================================================
    # 主入口
    # ============================================================
    async def process_all(self, skip_scan: bool = False):
        """
        执行完整流程
        
        Args:
            skip_scan: 是否跳过第一步和第二步
                - False: 先扫描，再生成二维码（适合首次运行）
                - True: 直接从分类列表生成二维码（适合已扫描完成）
        """
        if not skip_scan:
            await self.scan_all_products()
            await self.verify_no_sharebar()
        
        await self.generate_qr_and_merge()
        await self.export_html_and_pdf()
        
        self.log("\n" + "=" * 60)
        self.log("✅ 所有处理完成！")
        self.log(f"   有 Sharebar: {len(self.with_sharebar)} 个")
        self.log(f"   无 Sharebar: {len(self.without_sharebar)} 个")
        self.log(f"📁 输出目录: {self.config.EXPORTS_DIR}")
        self.log("=" * 60)