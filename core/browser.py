"""
浏览器管理模块 - 基于 Playwright
"""
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import Config


class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
    
    async def start(self):
        """启动浏览器"""
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.HEADLESS,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': self.config.VIEWPORT_WIDTH, 'height': self.config.VIEWPORT_HEIGHT},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        self.page = await self.context.new_page()
        print("✅ 浏览器启动完成")
        return self
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("✅ 浏览器已关闭")
    
    async def new_page(self):
        """创建新页面"""
        return await self.context.new_page()