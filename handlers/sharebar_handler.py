"""
Sharebar 链接获取 - Playwright 版本
移植自 Selenium 版本 5_login...py 的成功逻辑
"""
import asyncio
import re
from playwright.async_api import BrowserContext


class SharebarHandler:
    """Sharebar 链接处理器"""
    
    def __init__(self, context: BrowserContext):
        self.context = context
    
    async def get_sharebar_link(self, product_url: str, retry: int = 1) -> str:
        """获取产品的 Sharebar 链接（支持重试）"""
        
        for attempt in range(retry):
            if attempt > 0:
                print(f"   🔄 重试第 {attempt+1} 次...")
                await asyncio.sleep(2)
            
            result = await self._get_sharebar_once(product_url)
            if result:
                return result
        
        return None
    
    async def _get_sharebar_once(self, product_url: str) -> str:
        """单次获取 Sharebar 链接"""
        print(f"   🔗 获取 Sharebar...")
        
        page = await self.context.new_page()
        
        try:
            # 1. 打开产品页面
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # 2. 查找并点击 Sharebar 按钮
            sharebar_found = await self._find_and_click_sharebar(page)
            if not sharebar_found:
                print("   ⚠️ 未找到 Sharebar 按钮")
                return None
            
            # 3. 点击复制链接按钮
            copy_found = await self._click_copy_link(page)
            if not copy_found:
                print("   ⚠️ 未找到复制按钮")
                return None
            
            # 4. 获取剪贴板内容
            clipboard_text = await self._get_clipboard_content(page)
            if not clipboard_text:
                print("   ⚠️ 剪贴板内容为空")
                return None
            
            # 5. 提取 Sharebar URL
            sharebar_link = self._extract_sharebar_link(clipboard_text)
            if sharebar_link:
                print(f"   ✅ 获取到 Sharebar: {sharebar_link}")
                return sharebar_link
            else:
                print(f"   ⚠️ 未提取到有效 URL")
                return None
            
        except Exception as e:
            print(f"   ❌ Sharebar 获取失败: {e}")
            return None
        finally:
            await page.close()
    
    # ============================================================
    # 二次确认：对无 Sharebar 的产品重新检查
    # ============================================================
    async def verify_no_sharebar(self, product_url: str, max_retry: int = 3) -> dict:
        """
        二次确认产品是否真的没有 Sharebar
        返回: {'has_sharebar': bool, 'sharebar': str or None, 'attempts': int}
        """
        print(f"   🔍 二次确认 Sharebar...")
        
        for attempt in range(max_retry):
            if attempt > 0:
                print(f"   🔄 第 {attempt+1} 次尝试...")
                await asyncio.sleep(2)
            
            result = await self._get_sharebar_once(product_url)
            if result:
                return {
                    'has_sharebar': True,
                    'sharebar': result,
                    'attempts': attempt + 1
                }
        
        return {
            'has_sharebar': False,
            'sharebar': None,
            'attempts': max_retry
        }
    
    # ============================================================
    # 查找 Sharebar 按钮
    # ============================================================
    async def _find_and_click_sharebar(self, page) -> bool:
        """查找并点击 Sharebar 按钮"""
        print("   🔍 查找 Sharebar 按钮...")
        
        await asyncio.sleep(2)
        
        # 方法1: 通过文本查找
        sharebar_texts = [
            'ShareBarで紹介',
            'sharebarで紹介',
            'Sharebarで紹介',
            'sharebar',
            'Sharebar',
            'で紹介'
        ]
        
        for text in sharebar_texts:
            try:
                elements = await page.query_selector_all(f"xpath=//*[contains(text(), '{text}')]")
                for element in elements:
                    if await element.is_visible() and await element.is_enabled():
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await element.click()
                        print(f"   ✅ 点击 Sharebar 按钮: '{text}'")
                        await asyncio.sleep(3)
                        return True
            except:
                continue
        
        # 方法2: 通过 CSS 选择器查找
        css_selectors = [
            "button[class*='share']",
            "button[class*='Share']",
            "[class*='sharebar']",
            "[class*='Sharebar']",
            ".share-button",
        ]
        
        for selector in css_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible() and await element.is_enabled():
                        await element.scroll_into_view_if_needed()
                        await element.click()
                        print(f"   ✅ 点击 Sharebar 按钮: {selector}")
                        await asyncio.sleep(3)
                        return True
            except:
                continue
        
        print("   ❌ 未找到 Sharebar 按钮")
        return False
    
    # ============================================================
    # 点击复制链接按钮
    # ============================================================
    async def _click_copy_link(self, page) -> bool:
        """点击复制链接按钮 - 优先使用 CSS 选择器"""
        print("   🔍 查找复制按钮...")
        
        print("   ⏳ 等待 Sharebar 弹窗加载...")
        await asyncio.sleep(8)
        
        # ========== 方法1: CSS 选择器（Selenium 成功的方法） ==========
        css_selectors = [
            "[class*='copy']",
            "[class*='Copy']",
            "[class*='btn']",
            "[class*='button']",
            "[class*='share']",
            "[class*='Share']",
            "button",
            "a.btn",
            "div.btn"
        ]
        
        for selector in css_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible() and await element.is_enabled():
                        text = await element.text_content()
                        if text and any(kw in text for kw in ['コピー', 'Copy', 'copy', 'リンク']):
                            await element.click()
                            print(f"   ✅ 点击复制按钮: {selector}")
                            await asyncio.sleep(2)
                            return True
            except Exception as e:
                print(f"   ⚠️ CSS选择器 {selector} 失败: {e}")
        
        # ========== 方法2: 部分文本点击 ==========
        try:
            partial_texts = ["リンクをコピー", "コピー", "copy", "Copy"]
            for text in partial_texts:
                elements = await page.query_selector_all(f"xpath=//*[contains(text(), '{text}')]")
                for element in elements:
                    if await element.is_visible() and await element.is_enabled():
                        await element.click()
                        print(f"   ✅ 点击复制按钮: '{text}' (部分文本)")
                        await asyncio.sleep(2)
                        return True
        except Exception as e:
            print(f"   ⚠️ 部分文本失败: {e}")
        
        print("   ❌ 所有方法都未找到复制按钮")
        return False
    
    # ============================================================
    # 获取剪贴板内容
    # ============================================================
    async def _get_clipboard_content(self, page) -> str:
        """获取剪贴板内容"""
        print("   📋 读取剪贴板...")
        
        for i in range(3):
            try:
                clipboard_text = await page.evaluate("() => navigator.clipboard.readText()")
                if clipboard_text and clipboard_text.strip():
                    print(f"   ✅ 获取到剪贴板内容 ({len(clipboard_text)} 字符)")
                    return clipboard_text
            except:
                pass
            await asyncio.sleep(1)
        
        print("   ❌ 无法获取剪贴板内容")
        return None
    
    # ============================================================
    # 提取 Sharebar URL
    # ============================================================
    def _extract_sharebar_link(self, clipboard_content: str) -> str:
        """提取 Sharebar URL"""
        if not clipboard_content:
            return None
        
        urls = re.findall(r'https?://[^\s]+', clipboard_content)
        if not urls:
            return None
        
        # 优先选择 amwy.me 链接（Sharebar 短链）
        for url in urls:
            if 'amwy.me' in url:
                return url
        
        # 其次选择包含 sharebar 的链接
        for url in urls:
            if 'sharebar' in url.lower():
                return url
        
        # 返回第一个 URL
        return urls[0]