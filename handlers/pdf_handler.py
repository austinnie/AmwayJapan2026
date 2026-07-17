# handlers/pdf_handler.py
"""
PDF导出模块 - 将产品数据导出为PDF
"""
import os
import subprocess
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from .html_handler import HTMLHandler  # 复用HTML生成


class PDFHandler:
    """PDF处理器"""
    
    @staticmethod
    def html_to_pdf(html_path: Path, pdf_path: Path) -> bool:
        """
        将HTML转换为PDF
        
        支持多种转换方式:
        1. 使用 playwright (推荐，最稳定)
        2. 使用 wkhtmltopdf
        3. 使用 weasyprint
        """
        # 方法1: Playwright (推荐)
        if PDFHandler._convert_with_playwright(html_path, pdf_path):
            return True
        
        # 方法2: wkhtmltopdf
        if PDFHandler._convert_with_wkhtmltopdf(html_path, pdf_path):
            return True
        
        # 方法3: weasyprint
        if PDFHandler._convert_with_weasyprint(html_path, pdf_path):
            return True
        
        print("❌ 所有PDF转换方式都失败")
        return False
    
    @staticmethod
    def _convert_with_playwright(html_path: Path, pdf_path: Path) -> bool:
        """使用Playwright转换PDF"""
        try:
            from playwright.async_api import async_playwright
            import asyncio
            
            async def convert():
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    
                    # 加载HTML文件
                    await page.goto(f"file:///{html_path.absolute()}", wait_until="networkidle")
                    
                    # 导出PDF
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
            
            asyncio.run(convert())
            print(f"✅ PDF已生成 (Playwright): {pdf_path}")
            return True
            
        except Exception as e:
            print(f"⚠️ Playwright转换失败: {e}")
            return False
    
    @staticmethod
    def _convert_with_wkhtmltopdf(html_path: Path, pdf_path: Path) -> bool:
        """使用wkhtmltopdf转换PDF"""
        try:
            wkhtmltopdf_paths = [
                "wkhtmltopdf",
                r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
                r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
            ]
            
            for cmd in wkhtmltopdf_paths:
                if os.path.exists(cmd) or os.system(f"where {cmd} >nul 2>nul") == 0:
                    result = subprocess.run(
                        [cmd, str(html_path), str(pdf_path)],
                        capture_output=True,
                        timeout=30
                    )
                    if result.returncode == 0 and pdf_path.exists():
                        print(f"✅ PDF已生成 (wkhtmltopdf): {pdf_path}")
                        return True
                        
        except Exception as e:
            print(f"⚠️ wkhtmltopdf转换失败: {e}")
        return False
    
    @staticmethod
    def _convert_with_weasyprint(html_path: Path, pdf_path: Path) -> bool:
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
    def export_products(products: List[Dict], output_path: Path,
                        category_name: str = "全产品") -> bool:
        """
        导出产品数据为PDF
        内部先生成HTML，再转换为PDF
        """
        # 1. 先生成HTML
        html_handler = HTMLHandler()
        html_path = output_path.with_suffix('.html')
        
        if not html_handler.export_products(products, html_path, category_name):
            print("❌ HTML生成失败")
            return False
        
        # 2. 转换为PDF
        return PDFHandler.html_to_pdf(html_path, output_path)