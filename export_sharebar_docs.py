# export_sharebar_docs.py
"""
使用 Sharebar 版本的合并图片导出文档
优先使用 sharebar_merged_images 中的图片
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime

from config import Config
from handlers.html_handler import HTMLHandler
from handlers.pdf_handler import PDFHandler
from handlers.word_handler import WordHandler
from utils.file_utils import FileUtils


class SharebarDocExporter:
    """使用 Sharebar 图片导出文档"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.absolute()
        self.products_dir = self.base_dir / "products"
        self.exports_dir = self.products_dir / "exports"
        self.all_dir = self.products_dir / "all"
        
        self.file_utils = FileUtils(self.products_dir)
        self.html_handler = HTMLHandler()
        self.pdf_handler = PDFHandler()
        self.word_handler = WordHandler()
        
        # 目录
        self.image_dir = self.all_dir / "product_images"
        self.merged_dir = self.all_dir / "merged_images"
        self.sharebar_merged_dir = self.all_dir / "sharebar_merged_images"
        
        # 加载数据
        self.lang_mapping = self._load_json("product_lang_mapping.json")
        self.sharebar_mapping = self._load_json("sharebar_mapping.json")
        self.product_names = self._load_json("product_names.json")
        
        # 加载 URL 列表
        self.with_sharebar_urls = self._load_urls("list-withsharebar.txt")
        self.without_sharebar_urls = self._load_urls("list-withoutsharebar.txt")
        
        print(f"\n📊 加载完成:")
        print(f"   有 Sharebar: {len(self.with_sharebar_urls)}")
        print(f"   无 Sharebar: {len(self.without_sharebar_urls)}")
        print(f"   Sharebar 合并图片目录: {self.sharebar_merged_dir}")
    
    def _load_json(self, filename: str) -> dict:
        file_path = self.products_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _load_urls(self, filename: str) -> list:
        file_path = self.products_dir / filename
        urls = []
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and 'amwaylive.com' in line:
                        urls.append(line)
        return urls
    
    def _get_product_name(self, product_id: str) -> str:
        return self.product_names.get(product_id, f"产品 {product_id}")
    
    def _get_sharebar(self, product_id: str) -> str:
        return self.sharebar_mapping.get(product_id)
    
    def _build_product_info(self, url: str, has_sharebar: bool = True) -> dict:
        """构建产品信息"""
        product_id = self.file_utils.extract_product_id(url)
        product_name = self._get_product_name(product_id)
        lang_data = self.lang_mapping.get(product_id, {})
        sharebar = self._get_sharebar(product_id) if has_sharebar else None
        
        # 🔑 优先使用 Sharebar 合并图片
        sharebar_merged_path = self.sharebar_merged_dir / f"{product_id}_merged.png"
        if sharebar_merged_path.exists():
            img_path = str(sharebar_merged_path)
            merged_path = sharebar_merged_path
        else:
            # 降级使用原有 merged_images
            merged_path = self.merged_dir / f"{product_id}_merged.png"
            if merged_path.exists():
                img_path = str(merged_path)
            else:
                image_path = self.image_dir / f"{product_id}.png"
                img_path = str(image_path) if image_path.exists() else None
                merged_path = None
        
        return {
            'product_id': product_id,
            'url': url,
            'name': product_name,
            'name_ja': lang_data.get('ja', product_name),
            'name_zh': lang_data.get('zh', ''),
            'name_en': lang_data.get('en', ''),
            'image_path': img_path,
            'sharebar': sharebar,
            'has_sharebar': has_sharebar,
            'merged_path': str(merged_path) if merged_path and merged_path.exists() else None,
            'lang': lang_data
        }
    
    async def export(self):
        """导出所有文档"""
        print("\n" + "=" * 60)
        print("📄 使用 Sharebar 合并图片导出文档")
        print("=" * 60)
        
        # 构建产品列表
        all_products = []
        with_sharebar_products = []
        without_sharebar_products = []
        
        # 有 Sharebar 的产品
        for url in self.with_sharebar_urls:
            info = self._build_product_info(url, has_sharebar=True)
            all_products.append(info)
            with_sharebar_products.append(info)
        
        # 无 Sharebar 的产品
        for url in self.without_sharebar_urls:
            info = self._build_product_info(url, has_sharebar=False)
            all_products.append(info)
            without_sharebar_products.append(info)
        
        print(f"\n📊 产品统计:")
        print(f"   有 Sharebar: {len(with_sharebar_products)}")
        print(f"   无 Sharebar: {len(without_sharebar_products)}")
        print(f"   共: {len(all_products)}")
        
        # 检查有多少产品使用了 Sharebar 图片
        sharebar_img_count = sum(
            1 for p in all_products 
            if p.get('image_path') and 'sharebar_merged_images' in p['image_path']
        )
        print(f"   ✅ 使用 Sharebar 合并图片: {sharebar_img_count}")
        
        # 导出目录
        exports_dir = self.exports_dir
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        # 导出全产品
        base_name = "安利日本产品目录_Sharebar版"
        html_path = exports_dir / f"{base_name}.html"
        pdf_path = exports_dir / f"{base_name}.pdf"
        word_path = exports_dir / f"{base_name}.docx"
        
        print(f"\n📄 导出全产品...")
        self.html_handler.export_products(all_products, html_path, "全产品(Sharebar版)")
        await self.pdf_handler.export_products(all_products, pdf_path, "全产品(Sharebar版)")
        self.word_handler.export_products(all_products, word_path, "全产品(Sharebar版)")
        
        # 导出有 Sharebar 的产品
        if with_sharebar_products:
            print(f"📄 导出有 Sharebar 产品...")
            base_name = "有Sharebar产品_Sharebar版"
            html_path = exports_dir / f"{base_name}.html"
            pdf_path = exports_dir / f"{base_name}.pdf"
            word_path = exports_dir / f"{base_name}.docx"
            
            self.html_handler.export_products(with_sharebar_products, html_path, "有Sharebar产品(Sharebar版)")
            await self.pdf_handler.export_products(with_sharebar_products, pdf_path, "有Sharebar产品(Sharebar版)")
            self.word_handler.export_products(with_sharebar_products, word_path, "有Sharebar产品(Sharebar版)")
        
        # 导出无 Sharebar 的产品
        if without_sharebar_products:
            print(f"📄 导出无 Sharebar 产品...")
            base_name = "无Sharebar产品_Sharebar版"
            html_path = exports_dir / f"{base_name}.html"
            pdf_path = exports_dir / f"{base_name}.pdf"
            word_path = exports_dir / f"{base_name}.docx"
            
            self.html_handler.export_products(without_sharebar_products, html_path, "无Sharebar产品(Sharebar版)")
            await self.pdf_handler.export_products(without_sharebar_products, pdf_path, "无Sharebar产品(Sharebar版)")
            self.word_handler.export_products(without_sharebar_products, word_path, "无Sharebar产品(Sharebar版)")
        
        print("\n" + "=" * 60)
        print("✅ 导出完成!")
        print(f"📁 输出目录: {exports_dir}")
        print("=" * 60)


async def main():
    exporter = SharebarDocExporter()
    await exporter.export()


if __name__ == "__main__":
    asyncio.run(main())