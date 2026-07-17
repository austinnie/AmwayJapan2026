"""
登录模块测试
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from core.browser import BrowserManager
from core.login import LoginManager


async def test_login():
    print("=" * 50)
    print("测试: 登录功能")
    print("=" * 50)
    
    config = Config.ensure_directories()
    browser = await BrowserManager(config).start()
    
    try:
        login = LoginManager(browser.page, config)
        result = await login.login()
        
        if result:
            print("\n✅ 登录测试通过")
        else:
            print("\n❌ 登录测试失败")
            
        await asyncio.sleep(2)
        
    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_login())