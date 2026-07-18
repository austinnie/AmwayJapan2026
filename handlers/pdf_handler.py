# handlers/pdf_handler.py
"""
PDF导出模块 - 将产品数据导出为PDF
"""
import os
import subprocess
from pathlib import Path
from typing import List, Dict
from .html_handler import HTMLHandler


class PDFHandler:
    """PDF处理器"""
    
    async def html_to_pdf(self, html_path: Path, pdf_path: Path) -> bool:
        """将HTML转换为PDF"""
        # 方法1: Playwright (推荐)
        if await self._convert_with_playwright(html_path, pdf_path):
            return True
        
        # 方法2: wkhtmltopdf
        if self._convert_with_wkhtmltopdf(html_path, pdf_path):
            return True
        
        # 方法3: weasyprint
        if self._convert_with_weasyprint(html_path, pdf_path):
            return True
        
        print("❌ 所有PDF转换方式都失败")
        return False
    


    # handlers/pdf_handler.py

    async def _convert_with_playwright(self, html_path: Path, pdf_path: Path) -> bool:
        """使用Playwright转换PDF"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 🔑 使用绝对路径加载 HTML
                html_abs_path = html_path.absolute()
                await page.goto(f"file:///{html_abs_path}", wait_until="networkidle")
                
                # 等待图片加载
                await page.wait_for_timeout(2000)
                
                await page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "20mm",
                        "bottom": "20mm",
                        "left": "15mm",
                        "right": "15mm"
                    }
                )
                await browser.close()
            
            print(f"✅ PDF已生成: {pdf_path}")
            return True
            
        except Exception as e:
            print(f"⚠️ Playwright转换失败: {e}")
            return False
            
        
    def _convert_with_wkhtmltopdf(self, html_path: Path, pdf_path: Path) -> bool:
        """使用wkhtmltopdf转换PDF"""
        try:
            import shutil
            wkhtmltopdf_path = shutil.which("wkhtmltopdf")
            
            if not wkhtmltopdf_path:
                # Windows常见路径
                common_paths = [
                    r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
                    r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        wkhtmltopdf_path = path
                        break
            
            if not wkhtmltopdf_path:
                return False
            
            result = subprocess.run(
                [wkhtmltopdf_path, str(html_path), str(pdf_path)],
                capture_output=True,
                timeout=60
            )
            if result.returncode == 0 and pdf_path.exists():
                print(f"✅ PDF已生成 (wkhtmltopdf): {pdf_path}")
                return True
        except Exception as e:
            print(f"⚠️ wkhtmltopdf转换失败: {e}")
        return False
    
    def _convert_with_weasyprint(self, html_path: Path, pdf_path: Path) -> bool:
        """使用weasyprint转换PDF"""
        try:
            from weasyprint import HTML
            HTML(filename=str(html_path)).write_pdf(str(pdf_path))
            print(f"✅ PDF已生成 (weasyprint): {pdf_path}")
            return True
        except Exception as e:
            print(f"⚠️ weasyprint转换失败: {e}")
            return False
    
    @staticmethod
    async def export_products(products: List[Dict], output_path: Path,
                              category_name: str = "全产品") -> bool:
        """导出产品数据为PDF"""
        # 1. 先生成HTML
        html_handler = HTMLHandler()
        html_path = output_path.with_suffix('.html')
        
        if not html_handler.export_products(products, html_path, category_name, silent=True):
            print("❌ HTML生成失败")
            return False
        
        # 2. 转换为PDF
        handler = PDFHandler()
        return await handler.html_to_pdf(html_path, output_path)