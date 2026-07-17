"""
文件工具模块
"""
import re
from pathlib import Path
from typing import List


class FileUtils:
    """文件工具"""
    
    def __init__(self, products_dir: Path):
        self.products_dir = products_dir
        self.products_dir.mkdir(parents=True, exist_ok=True)
    
    def load_product_list(self, filename: str = "list-all.txt") -> List[str]:
        """加载产品列表"""
        file_path = self.products_dir / filename
        if not file_path.exists():
            print(f"⚠️ 文件不存在: {file_path}")
            return []
        
        urls = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#') or line.startswith('='):
                    continue
                if 'amwaylive.com/jp/products/' in line:
                    urls.append(line)
        
        print(f"📊 从 {filename} 加载了 {len(urls)} 个产品")
        return urls
    
    def extract_product_id(self, url: str) -> str:
        """从URL提取产品ID"""
        match = re.search(r'/products/(\d+)', url)
        return match.group(1) if match else "unknown"
    
    def get_category_dir(self, category_name: str) -> Path:
        """获取分类目录"""
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', category_name)
        category_dir = self.products_dir / safe_name
        category_dir.mkdir(parents=True, exist_ok=True)
        return category_dir