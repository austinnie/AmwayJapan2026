# translate_names.py
"""
产品名称多语言翻译工具
支持多种翻译引擎，可在配置中选择

运行: python translate_names.py
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class ProductNameTranslator:
    """产品名称翻译器 - 支持多种翻译引擎"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.absolute()
        self.products_dir = self.base_dir / "products"
        
        # 加载数据
        self.product_names = self._load_json("product_names.json")
        self.existing_mapping = self._load_json("product_lang_mapping.json")
        
        # 统计
        self.total = len(self.product_names)
        self.translated = 0
        self.skipped = 0
        self.failed = 0
        
        # 翻译引擎状态
        self.engines = {
            'google': {'available': False, 'name': 'Google Translate'},
            'deepl': {'available': False, 'name': 'DeepL'},
            'baidu': {'available': False, 'name': '百度翻译'},
            'local': {'available': True, 'name': '本地规则（不需要网络）'},
        }
        
        # 检测可用引擎
        self._check_engines()
    
    def _load_json(self, filename: str) -> dict:
        """加载JSON文件"""
        file_path = self.products_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_json(self, filename: str, data: dict):
        """保存JSON文件"""
        file_path = self.products_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _check_engines(self):
        """检测可用的翻译引擎"""
        print("=" * 60)
        print("🔍 检测翻译引擎...")
        print("=" * 60)
        
        # 1. Google Translate
        try:
            from deep_translator import GoogleTranslator
            self.engines['google']['available'] = True
            print("   ✅ Google Translate (deep-translator) 可用")
        except ImportError:
            print("   ⚠️ Google Translate 不可用 (需要: pip install deep-translator)")
        
        # 2. DeepL
        try:
            import deepl
            self.engines['deepl']['available'] = True
            print("   ✅ DeepL 可用")
        except ImportError:
            print("   ⚠️ DeepL 不可用 (需要: pip install deepl)")
        
        # 3. 百度翻译
        try:
            from baidu_translate import BaiduTranslator
            self.engines['baidu']['available'] = True
            print("   ✅ 百度翻译 可用")
        except ImportError:
            print("   ⚠️ 百度翻译 不可用 (需要: pip install baidu-translate)")
        
        # 4. 本地规则（始终可用）
        print("   ✅ 本地规则 可用")
        
        print("=" * 60)
        print()
    
    def _clean_name(self, name: str) -> str:
        """清理产品名称"""
        name = name.replace('\n', ' ').replace('\r', '')
        name = re.sub(r'\s+', ' ', name)
        
        suffixes = ['| アムウェイ', '| Amway', ' - Amway', '：Amway', ' | amwaylive']
        for suffix in suffixes:
            if suffix in name:
                name = name.split(suffix)[0].strip()
        name = re.sub(r'#\d+', '', name).strip()
        return name
    
    # ============================================================
    # 翻译引擎1: Google Translate (deep-translator)
    # ============================================================
    def _translate_google(self, text: str, target_lang: str) -> str:
        """Google Translate"""
        try:
            from deep_translator import GoogleTranslator
            
            lang_map = {
                'zh': 'zh-CN',
                'en': 'en',
                'ja': 'ja'
            }
            
            translator = GoogleTranslator(source='ja', target=lang_map.get(target_lang, target_lang))
            result = translator.translate(text)
            return result
        except Exception as e:
            print(f"   ⚠️ Google翻译失败: {e}")
            return ""
    
    # ============================================================
    # 翻译引擎2: DeepL
    # ============================================================
    def _translate_deepl(self, text: str, target_lang: str) -> str:
        """DeepL"""
        try:
            import deepl
            
            # 需要 API Key，请设置环境变量 DEEPL_API_KEY
            import os
            api_key = os.environ.get('DEEPL_API_KEY', '')
            
            if not api_key:
                print("   ⚠️ 请设置环境变量 DEEPL_API_KEY")
                return ""
            
            translator = deepl.Translator(api_key)
            
            lang_map = {
                'zh': 'ZH',
                'en': 'EN-US',
                'ja': 'JA'
            }
            
            result = translator.translate_text(text, target_lang=lang_map.get(target_lang, target_lang))
            return result.text
        except Exception as e:
            print(f"   ⚠️ DeepL翻译失败: {e}")
            return ""
    
    # ============================================================
    # 翻译引擎3: 百度翻译
    # ============================================================
    def _translate_baidu(self, text: str, target_lang: str) -> str:
        """百度翻译"""
        try:
            from baidu_translate import BaiduTranslator
            
            # 需要 APP ID 和 Secret Key
            import os
            appid = os.environ.get('BAIDU_APPID', '')
            secret = os.environ.get('BAIDU_SECRET', '')
            
            if not appid or not secret:
                print("   ⚠️ 请设置环境变量 BAIDU_APPID 和 BAIDU_SECRET")
                return ""
            
            translator = BaiduTranslator(appid, secret)
            
            lang_map = {
                'zh': 'zh',
                'en': 'en',
                'ja': 'jp'
            }
            
            result = translator.translate(text, from_lang='jp', to_lang=lang_map.get(target_lang, target_lang))
            return result
        except Exception as e:
            print(f"   ⚠️ 百度翻译失败: {e}")
            return ""
    
    # ============================================================
    # 翻译引擎4: 本地规则
    # ============================================================
    def _translate_local(self, text: str, target_lang: str) -> str:
        """本地规则翻译"""
        if target_lang == 'ja':
            return text
        
        # 常见词汇映射
        word_map = {
            'ja': {
                'スキン': ('肌肤', 'Skin'),
                'セラム': ('精华', 'Serum'),
                'クリーム': ('面霜', 'Cream'),
                'ローション': ('化妆水', 'Lotion'),
                'ウォッシュ': ('洁面', 'Wash'),
                'クレンジング': ('卸妆', 'Cleansing'),
                'オイル': ('油', 'Oil'),
                'マスク': ('面膜', 'Mask'),
                'エッセンス': ('精华', 'Essence'),
                'リップ': ('唇部', 'Lip'),
                'アイ': ('眼部', 'Eye'),
                'フェイス': ('面部', 'Face'),
                'ハリ': ('紧致', 'Firmness'),
                'しっとり': ('滋润', 'Moist'),
                'さっぱり': ('清爽', 'Refreshing'),
                'ヘルシー': ('健康', 'Healthy'),
                'プログラム': ('程序', 'Program'),
                'モイスチャー': ('保湿', 'Moisture'),
                'ジェル': ('凝胶', 'Gel'),
                'ミルキー': ('乳液', 'Milky'),
                'エマルジョン': ('乳液', 'Emulsion'),
                'パウダー': ('粉末', 'Powder'),
                'ファンデーション': ('粉底', 'Foundation'),
                'コンシーラー': ('遮瑕', 'Concealer'),
                'マスカラ': ('睫毛膏', 'Mascara'),
                'アイライナー': ('眼线', 'Eyeliner'),
                'リップスティック': ('口红', 'Lipstick'),
            }
        }
        
        result = text
        for ja, (zh, en) in word_map.get('ja', {}).items():
            if ja in result:
                if target_lang == 'zh':
                    result = result.replace(ja, zh)
                elif target_lang == 'en':
                    result = result.replace(ja, en)
        
        # 清理多余空格
        result = re.sub(r'\s+', ' ', result).strip()
        return result
    
    # ============================================================
    # 主翻译方法
    # ============================================================
    def translate(self, engine: str = 'google', interactive: bool = False):
        """
        执行翻译
        
        Args:
            engine: 翻译引擎
                - 'google': Google Translate (需要 deep-translator)
                - 'deepl': DeepL (需要 API Key)
                - 'baidu': 百度翻译 (需要 APP ID)
                - 'local': 本地规则 (不需要网络)
                - 'auto': 自动选择可用的
            interactive: 是否交互式
        """
        print("=" * 60)
        print(f"🌐 翻译引擎: {self.engines.get(engine, {}).get('name', engine)}")
        print("=" * 60)
        print(f"📊 产品总数: {self.total}")
        print(f"📊 已有映射: {len(self.existing_mapping)}")
        print(f"📊 需要翻译: {self.total - len(self.existing_mapping)}")
        print("=" * 60)
        print()
        
        # 检查引擎可用性
        if engine != 'local' and engine != 'auto':
            if not self.engines.get(engine, {}).get('available', False):
                print(f"❌ {engine} 不可用，请安装相应依赖")
                print("   Google: pip install deep-translator")
                print("   DeepL: pip install deepl")
                print("   百度: pip install baidu-translate")
                return
        
        mapping = self.existing_mapping.copy()
        use_google = (engine == 'google' or engine == 'auto')
        use_deepl = (engine == 'deepl' or engine == 'auto')
        use_baidu = (engine == 'baidu' or engine == 'auto')
        use_local = (engine == 'local' or engine == 'auto')
        
        for product_id, name in self.product_names.items():
            # 跳过已翻译的
            if product_id in mapping:
                continue
            
            clean_name = self._clean_name(name)
            print(f"\n📦 [{product_id}] {clean_name[:40]}...")
            
            lang_data = {}
            
            for lang in ['zh', 'en', 'ja']:
                if lang == 'ja':
                    translation = clean_name
                    lang_data[lang] = translation
                    print(f"   📝 日文: {translation[:30]}...")
                    continue
                
                translation = ""
                
                # 尝试 Google
                if use_google and not translation:
                    translation = self._translate_google(clean_name, lang)
                
                # 尝试 DeepL
                if use_deepl and not translation:
                    translation = self._translate_deepl(clean_name, lang)
                
                # 尝试百度
                if use_baidu and not translation:
                    translation = self._translate_baidu(clean_name, lang)
                
                # 尝试本地规则
                if use_local and not translation:
                    translation = self._translate_local(clean_name, lang)
                
                if translation:
                    lang_data[lang] = translation
                    print(f"   📝 {self._get_lang_name(lang)}: {translation[:30]}...")
                else:
                    lang_data[lang] = clean_name
                    print(f"   ⚠️ {self._get_lang_name(lang)}: 使用日文")
            
            mapping[product_id] = lang_data
            self.translated += 1
            
            if interactive:
                print("\n   🔍 继续？ (y/n/exit)")
                choice = input("   > ").strip().lower()
                if choice == 'n':
                    print("   ⏭️ 跳过")
                    continue
                elif choice == 'exit':
                    print("   ⏹️ 退出")
                    break
        
        # 保存
        self._save_json("product_lang_mapping.json", mapping)
        
        print("\n" + "=" * 60)
        print("📊 翻译完成统计:")
        print(f"   ✅ 总产品数: {self.total}")
        print(f"   ✅ 已映射: {len(mapping)}")
        print(f"   ✅ 新翻译: {self.translated}")
        print(f"   ❌ 失败: {self.failed}")
        print(f"   📁 保存到: product_lang_mapping.json")
        print("=" * 60)
    
    def _get_lang_name(self, lang: str) -> str:
        """获取语言名称"""
        names = {
            'zh': '中文',
            'en': '英文',
            'ja': '日文'
        }
        return names.get(lang, lang)
    
    def manual_input(self):
        """手动输入翻译"""
        print("=" * 60)
        print("🖊️ 手动输入翻译")
        print("=" * 60)
        print("💡 输入格式: 产品ID:中文:英文")
        print("   例如: 1179:健康肌肤程序:Healthy Skin Program")
        print("   (留空跳过，输入 'done' 完成)")
        print("=" * 60)
        
        mapping = self.existing_mapping.copy()
        count = 0
        
        while True:
            line = input("\n📝 > ").strip()
            
            if not line:
                continue
            
            if line.lower() == 'done':
                break
            
            parts = line.split(':')
            if len(parts) < 3:
                print("❌ 格式错误，需要: 产品ID:中文:英文")
                continue
            
            product_id = parts[0].strip()
            zh = parts[1].strip()
            en = parts[2].strip()
            
            if not product_id:
                print("❌ 产品ID不能为空")
                continue
            
            # 获取日文名称
            ja = self.product_names.get(product_id, '')
            
            mapping[product_id] = {
                'zh': zh,
                'en': en,
                'ja': ja
            }
            count += 1
            print(f"✅ 已保存: {product_id} -> {zh}")
        
        self._save_json("product_lang_mapping.json", mapping)
        print(f"\n✅ 已保存 {count} 个翻译")
        print(f"📁 保存到: product_lang_mapping.json")
    
    def show_status(self):
        """显示当前状态"""
        print("\n" + "=" * 60)
        print("📊 翻译状态")
        print("=" * 60)
        print(f"   产品总数: {self.total}")
        print(f"   已映射: {len(self.existing_mapping)}")
        print(f"   未映射: {self.total - len(self.existing_mapping)}")
        print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="产品名称多语言翻译工具")
    parser.add_argument(
        "--engine",
        choices=['google', 'deepl', 'baidu', 'local', 'auto'],
        default='auto',
        help="翻译引擎: google, deepl, baidu, local, auto (自动选择)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="交互式模式（每步确认）"
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="手动输入翻译"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="显示当前状态"
    )
    
    args = parser.parse_args()
    
    translator = ProductNameTranslator()
    
    if args.status:
        translator.show_status()
    elif args.manual:
        translator.manual_input()
    else:
        translator.translate(engine=args.engine, interactive=args.interactive)


if __name__ == "__main__":
    main()