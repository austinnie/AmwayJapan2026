"""
图片处理模块 - 截图、裁剪、下载
"""
import io
from pathlib import Path
from PIL import Image
from playwright.async_api import Page


class ImageHandler:
    """图片处理器"""
    
    async def capture_product_image(self, page: Page, product_id: str, 
                                     save_dir: Path) -> Path:
        """截取产品图片"""
        print(f"   📸 截取产品图片...")
        
        try:
            # 滚动到顶部
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)
            
            # 方法1: 查找产品图片元素
            img_selectors = [
                "img[src*='product']",
                ".product-image img",
                ".main-image img",
                "[class*='gallery'] img",
                "img[alt*='product']",
                "img[alt*='商品']"
            ]
            
            for selector in img_selectors:
                try:
                    img_element = await page.query_selector(selector)
                    if img_element and await img_element.is_visible():
                        # 检查图片尺寸
                        box = await img_element.bounding_box()
                        if box and box['width'] > 200 and box['height'] > 200:
                            image_path = save_dir / f"{product_id}.png"
                            await img_element.screenshot(path=str(image_path))
                            print(f"   ✅ 产品图片已保存: {image_path}")
                            return image_path
                except:
                    continue
            
            # 方法2: 固定区域截图（备用）
            screenshot = await page.screenshot(full_page=False)
            image = Image.open(io.BytesIO(screenshot))
            
            width, height = image.size
            # 产品区域通常在页面左侧
            crop_area = (40, 140, int(width * 0.46), 720)
            cropped = image.crop(crop_area)
            
            image_path = save_dir / f"{product_id}.png"
            cropped.save(image_path)
            print(f"   ✅ 产品图片已保存 (备用): {image_path}")
            return image_path
            
        except Exception as e:
            print(f"   ❌ 截图失败: {e}")
            return None