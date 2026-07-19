# product_query.py
"""
产品查询工具 - 支持多语言查询
运行: python product_query.py
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional


class ProductQuery:
    """产品查询工具"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.absolute()
        self.products_dir = self.base_dir / "products"
        
        # 加载数据
        self.product_names = self._load_json("product_names.json")
        self.sharebar_mapping = self._load_json("sharebar_mapping.json")
        self.lang_mapping = self._load_json("product_lang_mapping.json")
        self.with_sharebar_urls = self._load_urls("list-withsharebar.txt")
        self.without_sharebar_urls = self._load_urls("list-withoutsharebar.txt")
        
        # 构建索引
        self._build_index()
        
        # 统计
        self.total = len(self.product_names)
    
    def _load_json(self, filename: str) -> dict:
        """加载JSON文件（支持BOM，打印错误信息）"""
        file_path = self.products_dir / filename
        if file_path.exists():
            try:
                # 🔑 使用 utf-8-sig 自动处理 BOM
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    print(f"✅ 加载 {filename}: {len(data)} 条记录")
                    return data
            except json.JSONDecodeError as e:
                print(f"❌ JSON格式错误 {filename}: {e}")
                print(f"   位置: line {e.lineno} column {e.colno}")
            except Exception as e:
                print(f"❌ 加载失败 {filename}: {e}")
        else:
            print(f"⚠️ 文件不存在: {file_path}")
        return {}
    
    def _load_urls(self, filename: str) -> list:
        """加载URL列表"""
        file_path = self.products_dir / filename
        urls = []
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and 'amwaylive.com' in line:
                        urls.append(line)
        return urls
    
    def _extract_product_id(self, url: str) -> str:
        """从URL提取产品ID"""
        match = re.search(r'/products/(\d+)', url)
        return match.group(1) if match else "unknown"
    
    def _build_index(self):
        """构建多语言搜索索引"""
        self.id_index = {}
        self.name_index = {}
        self.lang_index = {'zh': {}, 'en': {}, 'ja': {}}
        
        print(f"📊 产品名称: {len(self.product_names)} 个")
        print(f"📊 多语言映射: {len(self.lang_mapping)} 个")
        
        for product_id, name in self.product_names.items():
            # 产品ID索引
            self.id_index[product_id] = {
                'id': product_id,
                'name': name,
                'sharebar': self.sharebar_mapping.get(product_id),
                'has_sharebar': product_id in self._get_ids_with_sharebar(),
                'url': self._get_url_by_id(product_id),
                'lang': self.lang_mapping.get(product_id, {})
            }
            
            # 名称索引
            self._add_to_name_index(name, product_id)
            
            # 多语言索引
            lang_data = self.lang_mapping.get(product_id, {})
            for lang in ['zh', 'en', 'ja']:
                lang_name = lang_data.get(lang, '')
                if lang_name:
                    self._add_to_lang_index(lang, lang_name, product_id)
        
        print(f"📊 中文索引: {len(self.lang_index['zh'])} 个关键词")
        if self.lang_index['zh']:
            print(f"   示例: {list(self.lang_index['zh'].keys())[:5]}")
    
    def _get_ids_with_sharebar(self) -> set:
        """获取有Sharebar的产品ID集合"""
        ids = set()
        for url in self.with_sharebar_urls:
            ids.add(self._extract_product_id(url))
        return ids
    
    def _get_url_by_id(self, product_id: str) -> str:
        """根据产品ID获取URL"""
        for url in self.with_sharebar_urls:
            if self._extract_product_id(url) == product_id:
                return url
        for url in self.without_sharebar_urls:
            if self._extract_product_id(url) == product_id:
                return url
        return f"https://www.amwaylive.com/jp/products/{product_id}"
    
    def _add_to_name_index(self, name: str, product_id: str):
        """添加到名称索引（支持分词）"""
        words = re.split(r'[\s\n、，,;；.。!！?？()（）[\]【】\t]+', name)
        for word in words:
            word = word.strip()
            if word and len(word) > 1:
                if word not in self.name_index:
                    self.name_index[word] = []
                if product_id not in self.name_index[word]:
                    self.name_index[word].append(product_id)
    
    def _add_to_lang_index(self, lang: str, name: str, product_id: str):
        """添加到语言索引（支持分词）"""
        # 按空格、换行、特殊字符分割
        words = re.split(r'[\s\n、，,;；.。!！?？()（）[\]【】\t]+', name)
        for word in words:
            word = word.strip()
            if word and len(word) >= 2:
                if word not in self.lang_index[lang]:
                    self.lang_index[lang][word] = []
                if product_id not in self.lang_index[lang][word]:
                    self.lang_index[lang][word].append(product_id)
    
    def search(self, keyword: str, search_type: str = "auto") -> List[Dict]:
        """搜索产品"""
        if not keyword or not keyword.strip():
            return []
        
        keyword = keyword.strip()
        results = []
        
        # 自动检测搜索类型
        if search_type == "auto":
            if keyword.isdigit():
                search_type = "id"
            else:
                search_type = "name"
        
        # 按ID搜索
        if search_type == "id":
            if keyword in self.id_index:
                return [self.id_index[keyword]]
            return []
        
        # 按名称搜索（模糊匹配）
        if search_type == "name":
            results = self._search_by_name(keyword)
            if results:
                return results
            return self._search_by_lang(keyword)
        
        # 按多语言搜索
        if search_type in ['zh', 'en', 'ja']:
            return self._search_by_lang(keyword, search_type)
        
        return self._search_all(keyword)
    
    def _search_by_name(self, keyword: str) -> List[Dict]:
        """按名称搜索（模糊匹配）"""
        results = []
        seen_ids = set()
        
        # 包含匹配
        for word, ids in self.name_index.items():
            if keyword in word or word in keyword:
                for product_id in ids:
                    if product_id not in seen_ids:
                        seen_ids.add(product_id)
                        results.append(self.id_index[product_id])
        
        return results
    
    def _search_by_lang(self, keyword: str, lang: str = None) -> List[Dict]:
        """按多语言搜索（支持分词）"""
        results = []
        seen_ids = set()
        
        if lang is None:
            # 尝试所有语言
            for lang_name in ['zh', 'en', 'ja']:
                for word, ids in self.lang_index.get(lang_name, {}).items():
                    if keyword in word or word in keyword:
                        for product_id in ids:
                            if product_id not in seen_ids:
                                seen_ids.add(product_id)
                                results.append(self.id_index[product_id])
            return results
        else:
            # 指定语言
            for word, ids in self.lang_index.get(lang, {}).items():
                if keyword in word or word in keyword:
                    for product_id in ids:
                        if product_id not in seen_ids:
                            seen_ids.add(product_id)
                            results.append(self.id_index[product_id])
            return results
    
    def _search_all(self, keyword: str) -> List[Dict]:
        """尝试所有搜索方式"""
        if keyword.isdigit():
            result = self.search(keyword, "id")
            if result:
                return result
        
        result = self.search(keyword, "name")
        if result:
            return result
        
        result = self.search(keyword, "zh")
        if result:
            return result
        
        return []
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """获取单个产品信息"""
        return self.id_index.get(product_id)
    
    def get_lang_names(self, product_id: str) -> Dict[str, str]:
        """获取产品的多语言名称"""
        return self.lang_mapping.get(product_id, {})
    
    def search_by_id(self, product_id: str) -> Optional[Dict]:
        """按产品ID精确搜索"""
        return self.id_index.get(product_id)
    
    def get_all_products(self) -> List[Dict]:
        """获取所有产品"""
        return list(self.id_index.values())
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with_sharebar = len(self.with_sharebar_urls)
        without_sharebar = len(self.without_sharebar_urls)
        
        return {
            'total': self.total,
            'with_sharebar': with_sharebar,
            'without_sharebar': without_sharebar,
            'with_lang_mapping': len(self.lang_mapping),
        }


def print_product(product: Dict):
    """打印产品信息"""
    print()
    print("=" * 60)
    print(f"📦 产品ID: {product['id']}")
    print(f"📝 日文: {product['name']}")
    # 显示多语言名称
    lang = product.get('lang', {})
    if lang.get('zh'):
        print(f"📝 中文: {lang['zh']}")
    if lang.get('en'):
        print(f"📝 英文: {lang['en']}")
    print(f"🔗 Sharebar: {product['sharebar'] or '无'}")
    print(f"📊 状态: {'✅ 有Sharebar' if product['has_sharebar'] else '❌ 无Sharebar'}")
    print(f"🔗 URL: {product['url']}")
    print("=" * 60)


def main():
    """交互式查询"""
    query = ProductQuery()
    
    print("=" * 60)
    print("🛍️ 安利日本产品查询工具")
    print("=" * 60)
    print(f"📊 共 {query.total} 个产品")
    print(f"📊 有Sharebar: {len(query.with_sharebar_urls)} 个")
    print(f"📊 无Sharebar: {len(query.without_sharebar_urls)} 个")
    print()
    print("💡 支持查询方式:")
    print("   • 产品ID: 1179")
    print("   • 日文: ヘルシースキン")
    print("   • 中文: 面霜, 精华, 洁面")
    print("   • 英文: cream, serum")
    print("   • 模糊搜索: スキン")
    print()
    print("📋 命令:")
    print("   • q [关键词]  - 查询产品")
    print("   • list         - 显示所有产品")
    print("   • stats        - 显示统计信息")
    print("   • help         - 显示帮助")
    print("   • exit         - 退出")
    print("=" * 60)
    
    while True:
        try:
            cmd = input("\n🔍 > ").strip()
            
            if not cmd:
                continue
            
            if cmd.lower() == 'exit' or cmd.lower() == 'quit':
                print("👋 再见！")
                break
            
            if cmd.lower() == 'help':
                print("\n💡 查询示例:")
                print("   q 1179          - 按ID查询")
                print("   q ヘルシースキン - 按日文查询")
                print("   q 面霜           - 按中文查询")
                print("   q cream         - 按英文查询")
                print("   list            - 显示所有产品")
                print("   stats           - 显示统计信息")
                continue
            
            if cmd.lower() == 'stats':
                stats = query.get_statistics()
                print(f"\n📊 统计信息:")
                print(f"   产品总数: {stats['total']}")
                print(f"   有Sharebar: {stats['with_sharebar']}")
                print(f"   无Sharebar: {stats['without_sharebar']}")
                print(f"   多语言映射: {stats['with_lang_mapping']}")
                continue
            
            if cmd.lower() == 'list':
                products = query.get_all_products()
                print(f"\n📋 共 {len(products)} 个产品:")
                for p in products[:20]:
                    status = "✅" if p['has_sharebar'] else "❌"
                    lang = p.get('lang', {})
                    name = lang.get('zh', p['name'])[:25]
                    print(f"   {status} {p['id']}: {name}...")
                if len(products) > 20:
                    print(f"   ... 还有 {len(products) - 20} 个产品")
                continue
            
            if cmd.startswith('q '):
                keyword = cmd[2:].strip()
            else:
                keyword = cmd
            
            results = query.search(keyword)
            
            if results:
                print(f"\n📊 找到 {len(results)} 个匹配产品:")
                for product in results:
                    print_product(product)
            else:
                print(f"\n❌ 未找到匹配 '{keyword}' 的产品")
                print("💡 提示: 试试按产品ID或日文名称搜索")
                
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")


def quick_search(keyword: str):
    """命令行快速查询"""
    query = ProductQuery()
    results = query.search(keyword)
    
    if results:
        print(f"\n📊 找到 {len(results)} 个匹配产品:")
        for product in results:
            print_product(product)
    else:
        print(f"\n❌ 未找到匹配 '{keyword}' 的产品")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        quick_search(" ".join(sys.argv[1:]))
    else:
        main()