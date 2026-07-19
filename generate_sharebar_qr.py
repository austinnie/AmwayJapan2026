# generate_sharebar_qr.py
"""
为有 Sharebar 的产品重新生成二维码和合并图片（使用 Sharebar URL）
新建目录 sharebar_qr_codes 和 sharebar_merged_images，与 product_images 同级
"""
import json
from pathlib import Path
from handlers.qr_handler import QRHandler


class SharebarQRGenerator:
    """为有 Sharebar 的产品重新生成二维码"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.absolute()
        self.products_dir = self.base_dir / "products"
        self.all_dir = self.products_dir / "all"
        
        self.qr_handler = QRHandler()
        
        # 输入目录
        self.product_images_dir = self.all_dir / "product_images"
        self.merged_images_dir = self.all_dir / "merged_images"
        
        # 🔑 输出目录（与 product_images 同级）
        self.output_qr_dir = self.all_dir / "sharebar_qr_codes"
        self.output_merged_dir = self.all_dir / "sharebar_merged_images"
        
        self.output_qr_dir.mkdir(parents=True, exist_ok=True)
        self.output_merged_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载数据
        self.sharebar_mapping = self._load_json("sharebar_mapping.json")
        self.lang_mapping = self._load_json("product_lang_mapping.json")
        self.product_names = self._load_json("product_names.json")
        self.with_sharebar_urls = self._load_urls("list-withsharebar.txt")
        
        # 统计
        self.success_count = 0
        self.skip_count = 0
        self.fail_count = 0
        self.total = len(self.sharebar_mapping)
        
        print(f"\n📊 加载完成:")
        print(f"   Sharebar 映射: {len(self.sharebar_mapping)}")
        print(f"   有 Sharebar 产品: {len(self.with_sharebar_urls)}")
        print()
        print(f"📁 输出目录:")
        print(f"   📱 二维码: {self.output_qr_dir}")
        print(f"   🖼️  合并图片: {self.output_merged_dir}")
    
    def _load_json(self, filename: str) -> dict:
        """加载 JSON 文件"""
        file_path = self.products_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 加载 {filename} 失败: {e}")
        return {}
    
    def _load_urls(self, filename: str) -> list:
        """加载 URL 列表"""
        file_path = self.products_dir / filename
        urls = []
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and 'amwaylive.com' in line:
                        urls.append(line)
        return urls
    
    def run(self):
        """执行重新生成"""
        print("\n" + "=" * 60)
        print("🔄 使用 Sharebar URL 重新生成二维码和合并图片")
        print("=" * 60)
        print(f"📊 共 {self.total} 个有 Sharebar 的产品需要处理")
        print("=" * 60)
        
        # 先列出前10个产品
        print("\n📋 有 Sharebar 的产品列表（前10个）:")
        for i, (pid, sharebar) in enumerate(list(self.sharebar_mapping.items())[:10], 1):
            name = self.lang_mapping.get(pid, {}).get('ja', self.product_names.get(pid, pid))
            print(f"   {i}. {pid}: {name[:30]}...")
        if self.total > 10:
            print(f"   ... 还有 {self.total - 10} 个")
        
        print("\n" + "-" * 60)
        
        # 处理每个产品
        for i, (product_id, sharebar_url) in enumerate(self.sharebar_mapping.items(), 1):
            print(f"\n📦 [{i}/{self.total}] 产品: {product_id}")
            
            # 获取名称
            name_ja = self.lang_mapping.get(product_id, {}).get('ja', 
                       self.product_names.get(product_id, product_id))
            print(f"   📝 {name_ja[:40]}...")
            print(f"   🔗 Sharebar: {sharebar_url[:30]}...")
            
            # 查找产品图片
            image_path = self._find_image(product_id)
            
            if not image_path:
                print(f"   ⚠️ 无图片，跳过")
                self.skip_count += 1
                continue
            
            print(f"   📸 使用图片: {image_path.name}")
            
            # 🔑 生成二维码（使用 Sharebar URL）
            qr_path = self.output_qr_dir / f"{product_id}_qr.png"
            qr_result = self.qr_handler.generate_qr(sharebar_url, qr_path)
            
            if not qr_result:
                print(f"   ❌ 二维码生成失败")
                self.fail_count += 1
                continue
            
            # 🔑 合并图片
            merged_path = self.output_merged_dir / f"{product_id}_merged.png"
            merge_result = self.qr_handler.merge_with_image(
                image_path, qr_path, merged_path
            )
            
            if merge_result:
                print(f"   ✅ 完成")
                self.success_count += 1
            else:
                print(f"   ❌ 合并失败")
                self.fail_count += 1
        
        # 输出统计
        self._print_summary()
    
    def _find_image(self, product_id: str) -> Path:
        """查找产品图片，优先使用已合并的图片"""
        # 1. 优先使用 merged_images 中的合并图片
        merged_path = self.merged_images_dir / f"{product_id}_merged.png"
        if merged_path.exists():
            return merged_path
        
        # 2. 尝试 merged_images 中的原始图片（不带 _merged 后缀）
        merged_path2 = self.merged_images_dir / f"{product_id}.png"
        if merged_path2.exists():
            return merged_path2
        
        # 3. 使用 product_images 中的原始图片
        product_path = self.product_images_dir / f"{product_id}.png"
        if product_path.exists():
            return product_path
        
        return None
    
    def _print_summary(self):
        """打印统计信息"""
        print("\n" + "=" * 60)
        print("📊 处理完成统计:")
        print(f"   ✅ 成功: {self.success_count}")
        print(f"   ⏭️  跳过（无图片）: {self.skip_count}")
        print(f"   ❌ 失败: {self.fail_count}")
        print(f"   📊 总计: {self.total}")
        print()
        print(f"📁 输出目录（与 product_images 同级）:")
        print(f"   📱 二维码: {self.output_qr_dir}")
        print(f"   🖼️  合并图片: {self.output_merged_dir}")
        print("=" * 60)


def main():
    generator = SharebarQRGenerator()
    generator.run()


if __name__ == "__main__":
    main()