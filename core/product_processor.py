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
        
        # 🔑 修复：只在有浏览器时才初始化 SharebarHandler
        if browser is not None and hasattr(browser, 'context'):
            self.sharebar_handler = SharebarHandler(browser.context)
        else:
            self.sharebar_handler = None
        
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
            # 🔑 获取产品名称（传递 product_id 作为备用）
            product_name = await self._extract_product_name(page, product_id)
            
            # 2. 获取产品图片
            category_dirs = self.file_utils.get_category_dir("all")
            image_dir = category_dirs / "product_images"
            image_dir.mkdir(parents=True, exist_ok=True)
            
            image_path = await self.image_handler.capture_product_image(
                page, product_id, image_dir
            )
            
            # 3. 尝试获取 Sharebar
            sharebar = await self.sharebar_handler.get_sharebar_link(url, retry=1)

            # 4. 🔑 保存产品名称到映射文件
            self._save_product_name(product_id, product_name)
        
            # 5. 记录结果
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
                # 🔑 关键：立即保存 Sharebar 映射
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
        """保存产品名称到文件"""
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
        """从文件读取产品名称"""
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
        """保存 Sharebar 映射到文件（持久化）"""
        import json
        mapping_file = self.config.PRODUCTS_DIR / "sharebar_mapping.json"
        
        # 加载现有数据
        data = {}
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                pass
        
        # 更新
        data[product_id] = sharebar
        
        # 保存
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


    def _get_sharebar_from_mapping(self, product_id: str) -> str:
        """从映射文件读取 Sharebar 链接"""
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
        """实时追加到分类列表"""
        filename = f"list-{category}.txt"
        file_path = self.config.PRODUCTS_DIR / filename
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f"{url}\n")
            
    async def _extract_product_name(self, page, product_id: str = "") -> str:
        """提取产品名称"""
        try:
            # 🔑 方法1: 从页面标题提取
            title = await page.title()
            if title:
                # 安利日本页面标题格式: "产品名称 | アムウェイ" 或 "产品名称 ：Amway"
                # 或者 "(ヘルシースキン プログラム) ：Amway(日本アムウェイ) | amwaylive"
                
                # 移除网站名称后缀（多种格式）
                suffixes = [
                    ' | アムウェイ',
                    ' | Amway', 
                    ' - Amway',
                    '｜アムウェイ',
                    '：Amway',
                    '| amwaylive',
                    '｜amwaylive',
                    ' - amwaylive',
                ]
                
                product_name = title
                for suffix in suffixes:
                    if suffix in product_name:
                        product_name = product_name.split(suffix)[0].strip()
                        break
                
                # 如果还有 "：" 分隔符，取前半部分
                if '：' in product_name:
                    product_name = product_name.split('：')[0].strip()
                
                # 如果还有 "|" 分隔符，取前半部分
                if '|' in product_name:
                    product_name = product_name.split('|')[0].strip()
                
                # 如果还有 " - " 分隔符，取前半部分
                if ' - ' in product_name:
                    product_name = product_name.split(' - ')[0].strip()
                
                # 过滤掉过短的名称
                if product_name and len(product_name) > 2:
                    # 进一步清理：移除多余的括号
                    product_name = product_name.strip('()（）')
                    self.log(f"   ✅ 从标题提取: {product_name[:50]}...")
                    return product_name
            
            # 🔑 方法2: 从 meta og:title 提取
            meta_title = await page.get_attribute('meta[property="og:title"]', 'content')
            if meta_title:
                product_name = meta_title.strip()
                # 同样的清理逻辑
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
            
            # 🔑 方法3: 从页面 h1 提取
            h1_elements = await page.query_selector_all('h1')
            for h1 in h1_elements:
                text = await h1.inner_text()
                text = text.strip()
                if text and len(text) > 2 and len(text) < 100:
                    # 过滤掉明显的非产品名称
                    skip_words = ['おすすめ', 'キャンペーン', 'ログイン', 'メニュー', '検索', 'カート']
                    if not any(skip in text for skip in skip_words):
                        self.log(f"   ✅ 从h1提取: {text[:50]}...")
                        return text
            
        except Exception as e:
            self.log(f"   ⚠️ 提取名称异常: {e}")
        
        return f"产品 {product_id}" if product_id else "未知产品"
    
    
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
    # core/product_processor.py - 修改 generate_qr_and_merge

    # core/product_processor.py - 添加到 ProductProcessor 类中

    async def fetch_all_product_urls(self):
        """
        从网站获取所有产品URL
        遍历多个分类页面，提取所有产品链接
        """
        self.log("\n" + "=" * 60)
        self.log("🌐 从网站获取所有产品列表")
        self.log("=" * 60)
        
        if self.browser is None:
            self.log("❌ 浏览器未初始化", "error")
            return []
        
        page = await self.browser.context.new_page()
        all_urls = []
        
        try:
            # 🔑 定义要扫描的分类URL（根据网站实际结构）
            category_urls = [
                # 主产品页（可能包含所有产品）
                "https://www.amwaylive.com/jp/products",
                
                # 如果有分类页面，在这里添加
                # "https://www.amwaylive.com/jp/products?category=cosme",
                # "https://www.amwaylive.com/jp/products?category=hair",
                # ...
            ]
            
            for category_url in category_urls:
                self.log(f"📂 访问: {category_url}")
                await page.goto(category_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(3)
                
                # 🔑 尝试翻页获取所有产品
                page_num = 1
                while True:
                    self.log(f"   📄 第 {page_num} 页")
                    
                    # 等待产品加载
                    await asyncio.sleep(2)
                    
                    # 提取当前页的所有产品链接
                    links = await page.query_selector_all('a[href*="/products/"]')
                    self.log(f"      🔗 找到 {len(links)} 个链接")
                    
                    for link in links:
                        try:
                            href = await link.get_attribute('href')
                            if href and '/products/' in href:
                                if href.startswith('/'):
                                    href = 'https://www.amwaylive.com' + href
                                if href not in all_urls:
                                    all_urls.append(href)
                        except:
                            continue
                    
                    # 🔑 尝试点击下一页
                    try:
                        next_button = await page.query_selector('a[rel="next"], .pagination .next, [class*="next"]')
                        if next_button and await next_button.is_visible() and await next_button.is_enabled():
                            await next_button.click()
                            await asyncio.sleep(2)
                            page_num += 1
                        else:
                            self.log(f"   ✅ 没有更多页面")
                            break
                    except:
                        self.log(f"   ✅ 没有更多页面")
                        break
            
            # 去重并按数字ID排序
            unique_urls = list(set(all_urls))
            
            def extract_id(url):
                import re
                match = re.search(r'/products/(\d+)', url)
                return int(match.group(1)) if match else 0
            
            unique_urls.sort(key=extract_id)
            
            self.log(f"\n📊 共获取到 {len(unique_urls)} 个产品")
            
            # 保存到文件
            output_file = self.config.PRODUCTS_DIR / "list-all-fetched.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                for url in unique_urls:
                    f.write(f"{url}\n")
            self.log(f"✅ 已保存到: {output_file}")
            
            # 与现有列表对比
            existing_file = self.config.PRODUCTS_DIR / "list-all.txt"
            if existing_file.exists():
                existing_urls = []
                with open(existing_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and 'amwaylive.com' in line:
                            existing_urls.append(line)
                
                self.log(f"\n📊 对比结果:")
                self.log(f"   现有列表: {len(existing_urls)} 个")
                self.log(f"   抓取列表: {len(unique_urls)} 个")
                self.log(f"   新增产品: {len(set(unique_urls) - set(existing_urls))} 个")
                self.log(f"   缺失产品: {len(set(existing_urls) - set(unique_urls))} 个")
            
            return unique_urls
            
        except Exception as e:
            self.log(f"❌ 获取失败: {e}", "error")
            import traceback
            traceback.print_exc()
            return []
        finally:
            await page.close()
        
        
    async def generate_qr_and_merge(self):
        """第三步：生成二维码并合并图片（支持断点续传）"""
        self.log("\n" + "=" * 60)
        self.log("📱 第三步：生成二维码并合并图片")
        self.log("=" * 60)
        
        # 从分类列表读取
        with_sharebar_urls = self._load_urls_from_file("list-withsharebar.txt")
        without_sharebar_urls = self._load_urls_from_file("list-withoutsharebar.txt")
        
        all_urls = with_sharebar_urls + without_sharebar_urls
        self.log(f"📊 有Sharebar: {len(with_sharebar_urls)} 个")
        self.log(f"📊 无Sharebar: {len(without_sharebar_urls)} 个")
        self.log(f"📊 共 {len(all_urls)} 个产品需要处理")
        
        # 准备目录
        category_dirs = self.file_utils.get_category_dir("all")
        qr_dir = category_dirs / "qr_codes"
        qr_dir.mkdir(parents=True, exist_ok=True)
        merged_dir = category_dirs / "merged_images"
        merged_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载已处理的二维码进度
        processed_qr = self._load_qr_progress()
        has_sharebar_set = set(with_sharebar_urls)
        
        for i, url in enumerate(all_urls):
            product_id = self.file_utils.extract_product_id(url)
            
            # 跳过已处理的
            if product_id in processed_qr:
                self.log(f"⏭️ [{i+1}/{len(all_urls)}] 产品 {product_id} 已处理，跳过")
                continue
            
            # 检查图片是否存在
            image_path = category_dirs / "product_images" / f"{product_id}.png"
            if not image_path.exists():
                self.log(f"⚠️ [{i+1}/{len(all_urls)}] 产品 {product_id} 无图片，跳过")
                continue
            
            self.log(f"\n📦 [{i+1}/{len(all_urls)}] 处理产品: {product_id}")
            
            # 🔑 判断是否有 Sharebar
            if url in has_sharebar_set:
                # 1. 先从映射文件读取 Sharebar
                sharebar = self._get_sharebar_from_mapping(product_id)
                
                # 2. 如果映射文件没有，重新获取
                if not sharebar:
                    self.log(f"   🔄 重新获取 Sharebar...")
                    sharebar = await self.sharebar_handler.get_sharebar_link(url, retry=2)
                    if sharebar:
                        # 🔑 关键：重新获取后立即保存
                        self._save_sharebar_mapping(product_id, sharebar)
                        self.log(f"   ✅ 获取到 Sharebar: {sharebar}")
                    else:
                        self.log(f"   ⚠️ 未能获取 Sharebar，降级使用产品URL")
                
                # 3. 决定使用哪个 URL
                if sharebar:
                    qr_url = sharebar
                    qr_type = "Sharebar"
                    self.log(f"   📱 使用 Sharebar 生成二维码")
                else:
                    qr_url = url
                    qr_type = "产品URL(降级)"
                    self.log(f"   📱 降级使用产品URL生成二维码")
            else:
                # 无 Sharebar，直接使用产品URL
                qr_url = url
                qr_type = "产品URL"
                self.log(f"   📱 使用 {qr_type} 生成二维码")
            
            # 生成二维码
            qr_path = qr_dir / f"{product_id}_qr.png"
            qr_result = self.qr_handler.generate_qr(qr_url, qr_path)
            
            if qr_result:
                # 合并图片
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

    async def generate_qr_from_lists(self):
        """
        第三步：直接加载两个分类TXT文件，生成二维码
        - 有Sharebar：重新获取Sharebar链接并保存
        - 无Sharebar：直接用产品URL
        """
        self.log("\n" + "=" * 60)
        self.log("📱 第三步：从分类列表生成二维码并合并图片")
        self.log("=" * 60)
        
        # 1. 直接加载两个分类TXT文件
        with_sharebar_urls = self._load_urls_from_file("list-withsharebar.txt")
        without_sharebar_urls = self._load_urls_from_file("list-withoutsharebar.txt")
        
        self.log(f"📊 有Sharebar: {len(with_sharebar_urls)} 个")
        self.log(f"📊 无Sharebar: {len(without_sharebar_urls)} 个")
        self.log(f"📊 共 {len(with_sharebar_urls) + len(without_sharebar_urls)} 个产品需要处理")
        
        # 2. 准备目录
        category_dirs = self.file_utils.get_category_dir("all")
        qr_dir = category_dirs / "qr_codes"
        qr_dir.mkdir(parents=True, exist_ok=True)
        merged_dir = category_dirs / "merged_images"
        merged_dir.mkdir(parents=True, exist_ok=True)
        
        # 3. 加载已处理的二维码进度（断点续传）
        processed_qr = self._load_qr_progress()
        
        # 4. 创建快速查找集合
        with_set = set(with_sharebar_urls)
        
        # 5. 合并两个列表
        all_urls = with_sharebar_urls + without_sharebar_urls
        total = len(all_urls)
        
        for i, url in enumerate(all_urls):
            product_id = self.file_utils.extract_product_id(url)
            
            # 断点续传：跳过已处理的
            if product_id in processed_qr:
                self.log(f"⏭️ [{i+1}/{total}] 产品 {product_id} 已处理，跳过")
                continue
            
            # 检查图片是否存在
            image_path = category_dirs / "product_images" / f"{product_id}.png"
            if not image_path.exists():
                self.log(f"⚠️ [{i+1}/{total}] 产品 {product_id} 无图片，跳过")
                continue
            
            self.log(f"\n📦 [{i+1}/{total}] 处理产品: {product_id}")
            
            # 🔑 判断是否有 Sharebar
            if url in with_set:
                # 有Sharebar：重新获取
                self.log(f"   🔄 重新获取 Sharebar...")
                sharebar = await self.sharebar_handler.get_sharebar_link(url, retry=2)
                
                if sharebar:
                    # ✅ 保存到映射文件
                    self._save_sharebar_mapping(product_id, sharebar)
                    qr_url = sharebar
                    qr_type = "Sharebar"
                    self.log(f"   ✅ 获取到 Sharebar: {sharebar}")
                else:
                    # 获取失败，降级使用产品URL
                    qr_url = url
                    qr_type = "产品URL(降级)"
                    self.log(f"   ⚠️ 获取失败，使用产品URL")
            else:
                # 无Sharebar：直接用产品URL
                qr_url = url
                qr_type = "产品URL"
                self.log(f"   📱 使用 {qr_type} 生成二维码")
            
            # 生成二维码
            qr_path = qr_dir / f"{product_id}_qr.png"
            qr_result = self.qr_handler.generate_qr(qr_url, qr_path)
            
            if qr_result:
                # 合并图片
                merged_path = merged_dir / f"{product_id}_merged.png"
                merge_result = self.qr_handler.merge_with_image(
                    image_path, qr_path, merged_path
                )
                if merge_result:
                    self.log(f"   ✅ 合并完成")
                    # 立即保存进度
                    self._save_qr_progress(product_id)
                else:
                    self.log(f"   ❌ 合并失败")
            else:
                self.log(f"   ❌ 二维码生成失败")
            
            await asyncio.sleep(0.5)
        
        self.log("\n" + "=" * 60)
        self.log("✅ 二维码生成和图片合并完成！")
        self.log(f"   已处理: {len(self._load_qr_progress())} 个")
        self.log("=" * 60)


    def _load_urls_from_file(self, filename: str) -> List[str]:
        """从文件加载URL列表"""
        file_path = self.config.PRODUCTS_DIR / filename
        urls = []
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and 'amwaylive.com' in line:
                        urls.append(line)
        return urls


    def _save_sharebar_mapping(self, product_id: str, sharebar: str):
        """保存 Sharebar 映射到文件"""
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
        
    def _load_urls_from_file(self, filename: str) -> List[str]:
        """从文件加载URL列表"""
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
        """加载二维码处理进度"""
        progress_file = self.config.PRODUCTS_DIR  / "qr_progress.json"
        if progress_file.exists():
            try:
                import json
                with open(progress_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except:
                pass
        return set()

    def _save_qr_progress(self, product_id: str):
        """保存单个产品二维码处理进度"""
        import json
        progress_file = self.config.PRODUCTS_DIR  / "qr_progress.json"
        
        # 加载现有进度
        processed = self._load_qr_progress()
        processed.add(product_id)
        
        # 保存
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(list(processed), f, ensure_ascii=False, indent=2)
        
    # ============================================================
    # 第四步：导出 HTML 和 PDF
    # ============================================================
    # core/product_processor.py

    def _load_urls_from_file(self, filename: str) -> List[str]:
        """从文件加载URL列表"""
        file_path = self.config.PRODUCTS_DIR / filename
        urls = []
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and 'amwaylive.com' in line:
                        urls.append(line)
        return urls

    def _get_sharebar_from_mapping(self, product_id: str) -> str:
        """从映射文件读取 Sharebar 链接"""
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
        """第四步：导出 HTML 和 PDF 文档（直接从文件读取）"""
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
        
        # 1. 处理有Sharebar的产品
        for url in with_sharebar_urls:
            product_id = self.file_utils.extract_product_id(url)
            sharebar = self._get_sharebar_from_mapping(product_id)
            # 🔑 获取真实产品名称
            product_name = self._get_product_name(product_id)
        
            image_path = image_dir / f"{product_id}.png"
            merged_path = merged_dir / f"{product_id}_merged.png"
            
            product_info = {
                'product_id': product_id,
                'url': url,
                'name': product_name,  # ✅ 保证有值
                'image_path': str(image_path) if image_path.exists() else None,
                'sharebar': sharebar,
                'has_sharebar': True,
                'merged_path': str(merged_path) if merged_path.exists() else None
            }
            all_products.append(product_info)
            with_sharebar_products.append(product_info)
        
        # 2. 处理无Sharebar的产品
        for url in without_sharebar_urls:
            product_id = self.file_utils.extract_product_id(url)
            # 🔑 获取真实产品名称
            product_name = self._get_product_name(product_id)
        
            image_path = image_dir / f"{product_id}.png"
            merged_path = merged_dir / f"{product_id}_merged.png"
            
            product_info = {
                'product_id': product_id,
                'url': url,
                'name': product_name,  # ✅ 保证有值
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
        
        # 🔑 使用 exports 目录
        exports_dir = self.config.EXPORTS_DIR
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备图片复制（HTML需要引用图片）
        self._prepare_images_for_export(all_products)

   
        # 🔑 导入 WordHandler
        from handlers.word_handler import WordHandler
        word_handler = WordHandler()
    
        # 1. 导出全产品
        self.log("📄 导出全产品目录...")
        base_name = "安利日本产品目录"
        html_path = exports_dir  / f"{base_name}.html"
        pdf_path = exports_dir  / f"{base_name}.pdf"
        word_path = exports_dir  / f"{base_name}.docx"  # ✅ Word 路径
        
        self.html_handler.export_products(all_products, html_path, "全产品")
        await self.pdf_handler.export_products(all_products, pdf_path, "全产品")
        word_handler.export_products(all_products, word_path, "全产品")  # ✅ 导出 Word
        
        # 2. 导出有 Sharebar 产品
        if with_sharebar_products:
            self.log("📄 导出有 Sharebar 产品目录...")
            base_name = "有Sharebar产品"
            html_path = exports_dir  / f"{base_name}.html"
            pdf_path = exports_dir  / f"{base_name}.pdf"
            word_path = exports_dir  / f"{base_name}.docx"
            
            self.html_handler.export_products(with_sharebar_products, html_path, "有Sharebar产品")
            await self.pdf_handler.export_products(with_sharebar_products, pdf_path, "有Sharebar产品")
            word_handler.export_products(with_sharebar_products, word_path, "有Sharebar产品")
        
        # 3. 导出无 Sharebar 产品
        if without_sharebar_products:
            self.log("📄 导出无 Sharebar 产品目录...")
            base_name = "无Sharebar产品"
            html_path = exports_dir  / f"{base_name}.html"
            pdf_path = exports_dir  / f"{base_name}.pdf"
            word_path = exports_dir  / f"{base_name}.docx"
            
            self.html_handler.export_products(without_sharebar_products, html_path, "无Sharebar产品")
            await self.pdf_handler.export_products(without_sharebar_products, pdf_path, "无Sharebar产品")
            word_handler.export_products(without_sharebar_products, word_path, "无Sharebar产品")
        
        self.log("\n" + "=" * 60)
        self.log("✅ 文档导出完成!")
        self.log(f"📁 输出目录: {exports_dir }")
        self.log("=" * 60)
    
    def _prepare_images_for_export(self, products: List[Dict]):
        """准备导出用的图片（复制到输出目录）"""
        exports_dir = self.config.EXPORTS_DIR
        output_images_dir = exports_dir  / "images"
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
    async def process_all(self, skip_scan: bool = False):
        """
        执行完整流程
        
        Args:
            skip_scan: 是否跳过第一步和第二步
                - True: 直接从分类列表生成二维码（适合已扫描完成）
                - False: 先扫描，再生成二维码（适合首次运行）
        """
        if not skip_scan:
            # 第一步：扫描
            await self.scan_all_products()
            
            # 第二步：二次确认
            await self.verify_no_sharebar()
        
        # 第三步：直接从分类列表生成二维码（会重新获取Sharebar并保存）
        await self.generate_qr_from_lists()
        
        # 第四步：导出 HTML 和 PDF
        await self.export_html_and_pdf()
        
        self.log("\n" + "=" * 60)
        self.log("✅ 所有处理完成！")
        self.log(f"   有 Sharebar: {len(self.with_sharebar)} 个")
        self.log(f"   无 Sharebar: {len(self.without_sharebar)} 个")
        self.log(f"📁 输出目录: {self.config.EXPORTS_DIR}")  # ✅ 使用 self.config.EXPORTS_DIR
        self.log("=" * 60)