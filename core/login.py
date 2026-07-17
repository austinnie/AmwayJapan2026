"""
登录模块 - 优化等待时间
"""
from playwright.async_api import Page
from config import Config


class LoginManager:
    """登录管理器"""
    
    def __init__(self, page: Page, config: Config):
        self.page = page
        self.config = config
    
    async def login(self) -> bool:
        """执行登录"""
        print("🔐 开始登录...")
        
        try:
            # 1. 导航到登录页面
            await self.page.goto(self.config.LOGIN_URL, timeout=self.config.BROWSER_TIMEOUT)
            await self.page.wait_for_selector("#j_username", timeout=15000)
            print("   ✅ 登录页面加载完成")
            
            # 2. 输入用户名
            await self.page.fill("#j_username", self.config.USERNAME)
            print("   ✅ 用户名已输入")
            
            # 3. 输入密码
            await self.page.fill("#j_password", self.config.PASSWORD)
            print("   ✅ 密码已输入")
            
            # 4. 点击登录按钮
            await self._click_login_button()
            
            # 5. 等待跳转完成 - 使用更高效的等待方式
            print("   ⏳ 等待跳转...")
            
            # 等待URL变化，不再等待 networkidle（耗时太长）
            try:
                await self.page.wait_for_url(
                    lambda url: "amwaylive.com/jp" in url and "login" not in url.lower(),
                    timeout=30000
                )
            except:
                # 如果等待超时，检查当前URL
                pass
            
            # 6. 验证登录
            current_url = self.page.url
            print(f"   📍 当前URL: {current_url}")
            
            if "amwaylive.com/jp" in current_url and "login" not in current_url.lower():
                print("   ✅ 登录成功！")
                return True
            else:
                print(f"   ❌ 登录失败，当前URL: {current_url}")
                await self.page.screenshot(path="login_failed.png")
                return False
                
        except Exception as e:
            print(f"   ❌ 登录异常: {e}")
            await self.page.screenshot(path="login_error.png")
            return False
    
    async def _click_login_button(self):
        """精确点击'ログイン'按钮"""
        print("   🔍 查找登录按钮...")
        
        try:
            button = await self.page.query_selector(
                "//button[normalize-space()='ログイン']"
            )
            if button and await button.is_visible():
                await button.click()
                print("   ✅ 点击了登录按钮")
                return
        except:
            pass
        
        # 备用方法：遍历按钮
        try:
            buttons = await self.page.query_selector_all("button")
            for btn in buttons:
                if await btn.is_visible() and await btn.is_enabled():
                    text = await btn.text_content()
                    if text and text.strip() == "ログイン":
                        await btn.click()
                        print("   ✅ 点击了登录按钮")
                        return
        except:
            pass
        
        raise Exception("未找到'ログイン'按钮")