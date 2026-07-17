"""
Sharebar 链接获取 - Playwright 版本
移植自 Selenium 版本的成功逻辑
"""
import asyncio
import re
from playwright.async_api import BrowserContext


class SharebarHandler:
    """Sharebar 链接处理器"""
    
    def __init__(self, context: BrowserContext):
        self.context = context
    
    async def get_sharebar_link(self, product_url: str) -> str:
        """获取产品的 Sharebar 链接"""
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
            
            # 3. 点击复制链接按钮（关键：等待弹窗加载）
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
    
    async def _find_and_click_sharebar(self, page) -> bool:
        """查找并点击 Sharebar 按钮"""
        print("   🔍 查找 Sharebar 按钮...")
        
        await asyncio.sleep(2)
        
        # Sharebar 按钮文本变体
        sharebar_texts = [
            'ShareBarで紹介',
            'sharebarで紹介',
            'Sharebarで紹介',
            'sharebar',
            'Sharebar',
            'で紹介'
        ]
        
        # 方法1: 通过文本查找
        for text in sharebar_texts:
            try:
                elements = await page.query_selector_all(f"xpath=//*[contains(text(), '{text}')]")
                for element in elements:
                    if await element.is_visible() and await element.is_enabled():
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await element.click()
                        print(f"   ✅ 点击 Sharebar 按钮: '{text}'")
                        await asyncio.sleep(3)  # 等待弹窗出现
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
        

    async def _click_copy_link(self, page) -> bool:
        """点击复制链接按钮 - 精确定位'リンクをコピー'"""
        print("   🔍 查找复制按钮...")
        
        print("   ⏳ 等待 Sharebar 弹窗加载...")
        await asyncio.sleep(5)
        
        # ========== 方法1: 精确文本匹配 ==========
        try:
            # 精确匹配"リンクをコピー"文本
            elements = await page.query_selector_all("xpath=//*[text()='リンクをコピー']")
            for element in elements:
                if await element.is_visible():
                    await element.click()
                    print("   ✅ 点击复制按钮: リンクをコピー (精确匹配)")
                    await asyncio.sleep(2)
                    return True
        except:
            pass
        
        # ========== 方法2: 包含"リンク"和"コピー" ==========
        try:
            elements = await page.query_selector_all("xpath=//*[contains(text(), 'リンク') and contains(text(), 'コピー')]")
            for element in elements:
                if await element.is_visible():
                    # 确保不是 LINE/X/Facebook/WeChat
                    text = await element.text_content()
                    if text and 'リンク' in text and 'コピー' in text:
                        await element.click()
                        print(f"   ✅ 点击复制按钮: '{text.strip()}'")
                        await asyncio.sleep(2)
                        return True
        except:
            pass
        
        # ========== 方法3: CSS 选择器（排除社交按钮） ==========
        try:
            # 只找包含"copy"相关类名的元素
            selectors = [
                "[class*='copy']",
                "[class*='Copy']",
                "button:has-text('コピー')",
                "a:has-text('コピー')",
            ]
            
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        text = await element.text_content()
                        # 排除社交分享按钮
                        if text and any(kw in text for kw in ['コピー', 'Copy', 'copy']):
                            if 'LINE' not in text and 'Facebook' not in text and 'X' not in text and 'WeChat' not in text:
                                await element.click()
                                print(f"   ✅ 点击复制按钮: {selector}")
                                await asyncio.sleep(2)
                                return True
        except:
            pass
        
        # ========== 方法4: 遍历所有按钮，找"リンクをコピー" ==========
        try:
            buttons = await page.query_selector_all("button, a, [role='button']")
            for btn in buttons:
                if await btn.is_visible():
                    text = await btn.text_content()
                    if text:
                        text = text.strip().replace('\n', '').replace(' ', '')
                        # 精确匹配"リンクをコピー"（忽略换行和空格）
                        if text == 'リンクをコピー' or 'リンクをコピー' in text:
                            await btn.click()
                            print(f"   ✅ 点击复制按钮: '{text}' (遍历匹配)")
                            await asyncio.sleep(2)
                            return True
        except:
            pass
        
        # ========== 方法5: 截图调试 ==========
        await page.screenshot(path="sharebar_debug.png")
        print("   📸 截图已保存: sharebar_debug.png")
        
        print("   ❌ 未找到复制按钮")
        return False
    
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