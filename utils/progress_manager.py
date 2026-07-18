"""
进度管理 - 支持断点续传
"""
import json
from pathlib import Path
from typing import Set


class ProgressManager:
    """进度管理器"""
    
    def __init__(self, products_dir: Path):
        # 🔑 保存到 products 目录
        self.save_dir = products_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self.processed_file = self.save_dir / "processed_products.json"
        self.processed: Set[str] = set()
        
        self._load()
    
    def _load(self):
        if self.processed_file.exists():
            try:
                with open(self.processed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed = set(data)
                print(f"📊 加载进度: {len(self.processed)} 个产品已处理")
            except:
                pass
    
    def save(self):
        try:
            with open(self.processed_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.processed), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存进度失败: {e}")
    
    def is_processed(self, product_id: str) -> bool:
        return product_id in self.processed
    
    def mark_processed(self, product_id: str):
        self.processed.add(product_id)
    
    def reset(self):
        self.processed = set()
        if self.processed_file.exists():
            self.processed_file.unlink()
        print("🔄 进度已重置")