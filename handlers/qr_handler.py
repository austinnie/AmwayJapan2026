"""
二维码生成模块
"""
import qrcode
from pathlib import Path
from PIL import Image, ImageDraw


class QRHandler:
    """二维码处理器"""
    
    def generate_qr(self, url: str, save_path: Path) -> Path:
        """生成二维码"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img.save(save_path)
            print(f"   ✅ 二维码已生成: {save_path}")
            return save_path
            
        except Exception as e:
            print(f"   ❌ QR码生成失败: {e}")
            return None
    
    def merge_with_product(self, product_img_path: Path, qr_path: Path, 
                           save_path: Path) -> Path:
        """合并产品图片和二维码"""
        try:
            product_img = Image.open(product_img_path)
            qr_img = Image.open(qr_path)
            
            # 调整二维码大小（产品图宽度的1/4，最小100px，最大200px）
            qr_size = min(max(product_img.width // 4, 100), 200)
            qr_resized = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
            
            # 合并
            merged = product_img.copy()
            if merged.mode != 'RGBA':
                merged = merged.convert('RGBA')
            
            # 右下角位置
            margin = 20
            position = (merged.width - qr_size - margin, merged.height - qr_size - margin)
            
            # 白色背景
            draw = ImageDraw.Draw(merged)
            draw.rectangle(
                [position[0] - 10, position[1] - 10, 
                 position[0] + qr_size + 10, position[1] + qr_size + 10],
                fill=(255, 255, 255, 230)
            )
            
            merged.paste(qr_resized, position)
            merged.save(save_path)
            
            print(f"   ✅ 合并图片已保存: {save_path}")
            return save_path
            
        except Exception as e:
            print(f"   ❌ 合并失败: {e}")
            return None