# handlers/word_handler.py
"""
Word文档导出模块 - 使用 python-docx
"""
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT


class WordHandler:
    """Word文档处理器"""
    
    def __init__(self):
        self.doc = None
    
    def export_products(self, products: List[Dict], output_path: Path, 
                        category_name: str = "全产品") -> bool:
        """导出产品数据到Word文档"""
        try:
            self.doc = Document()
            
            self._add_title(category_name)
            self._add_stats(products)
            self._add_summary_table(products)
            self._add_product_details(products)
            
            self.doc.save(str(output_path))
            print(f"✅ Word文档已生成: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Word导出失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _add_title(self, category_name: str):
        """添加标题"""
        title = self.doc.add_heading(f"安利日本产品目录 - {category_name}", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        time_para = self.doc.add_paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        time_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.doc.add_paragraph()
    
    def _add_stats(self, products: List[Dict]):
        """添加统计信息"""
        total = len(products)
        with_sharebar = sum(1 for p in products if p.get('has_sharebar', False))
        without_sharebar = total - with_sharebar
        
        stats = self.doc.add_paragraph()
        stats.add_run("统计信息\n").bold = True
        stats.add_run(f"   * 产品总数: {total}\n")
        stats.add_run(f"   * 有Sharebar: {with_sharebar}\n")
        stats.add_run(f"   * 无Sharebar: {without_sharebar}")
        self.doc.add_paragraph()
    
    def _add_summary_table(self, products: List[Dict]):
        """添加产品汇总表格"""
        self.doc.add_heading("产品汇总表", level=1)
        
        table = self.doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        headers = ['序号', '产品ID', '产品名称', 'Sharebar状态', '链接']
        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = header
            cell.paragraphs[0].runs[0].bold = True
        
        for idx, product in enumerate(products, 1):
            row = table.add_row()
            row.cells[0].text = str(idx)
            
            # 🔑 安全获取值，确保不为 None
            product_id = product.get('product_id', '') or ''
            row.cells[1].text = product_id
            
            name = product.get('name', '未知产品') or '未知产品'
            row.cells[2].text = name[:30] if name else '未知产品'
            
            row.cells[3].text = '有' if product.get('has_sharebar') else '无'
            
            sharebar = product.get('sharebar', '') or ''
            url = product.get('url', '') or ''
            link = sharebar or url
            row.cells[4].text = link[:50] if link else '无'
        
        self.doc.add_paragraph()
    
    def _add_product_details(self, products: List[Dict]):
        """添加每个产品的详细信息页"""
        self.doc.add_page_break()
        self.doc.add_heading("产品详细信息", level=1)
        
        for idx, product in enumerate(products, 1):
            if idx > 1 and idx % 10 == 1:
                self.doc.add_page_break()
            
            name = product.get('name', '未知产品') or '未知产品'
            self.doc.add_heading(f"{idx}. {name}", level=2)
            
            info = self.doc.add_paragraph()
            
            product_id = product.get('product_id', '') or ''
            info.add_run("产品ID: ").bold = True
            info.add_run(f"{product_id}\n")
            
            url = product.get('url', '') or ''
            info.add_run("URL: ").bold = True
            info.add_run(f"{url}\n")
            
            sharebar = product.get('sharebar', '') or ''
            info.add_run("Sharebar: ").bold = True
            info.add_run(f"{sharebar if sharebar else '无'}\n")
            
            info.add_run("状态: ").bold = True
            info.add_run(f"{'有Sharebar' if product.get('has_sharebar') else '无Sharebar'}")
            
            merged_path = product.get('merged_path')
            if merged_path and Path(merged_path).exists():
                try:
                    para = self.doc.add_paragraph()
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = para.add_run()
                    run.add_picture(str(merged_path), width=Inches(4.0))
                except Exception as e:
                    self.doc.add_paragraph(f"[图片加载失败: {e}]")
            elif product.get('image_path') and Path(product['image_path']).exists():
                try:
                    para = self.doc.add_paragraph()
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = para.add_run()
                    run.add_picture(str(product['image_path']), width=Inches(3.0))
                except:
                    self.doc.add_paragraph("[无图片]")
            else:
                self.doc.add_paragraph("[无图片]")
            
            self.doc.add_paragraph('_' * 60)