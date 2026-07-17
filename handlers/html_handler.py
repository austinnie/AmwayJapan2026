# handlers/html_handler.py
"""
HTML导出模块 - 生成美观的产品展示页面
"""
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import json


class HTMLHandler:
    """HTML处理器"""
    
    TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>安利日本产品目录 - {category_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
            background: #f5f7fa;
            padding: 30px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        
        /* 头部 */
        .header {{
            text-align: center;
            padding: 40px 0 30px;
            background: linear-gradient(135deg, #1a237e, #0d47a1);
            color: white;
            border-radius: 12px;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .header .sub {{ opacity: 0.8; font-size: 14px; }}
        
        /* 统计卡片 */
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .stat-card .num {{ font-size: 28px; font-weight: bold; color: #1a237e; }}
        .stat-card .label {{ font-size: 13px; color: #666; margin-top: 4px; }}
        
        /* 产品网格 */
        .product-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 20px;
        }}
        .product-card {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .product-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }}
        .product-card .image {{
            width: 100%;
            height: 200px;
            object-fit: contain;
            background: #fafafa;
            padding: 10px;
        }}
        .product-card .info {{
            padding: 12px 16px 16px;
        }}
        .product-card .id {{
            font-size: 12px;
            color: #999;
            margin-bottom: 4px;
        }}
        .product-card .name {{
            font-size: 14px;
            font-weight: 600;
            color: #1a237e;
            margin-bottom: 6px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            height: 40px;
        }}
        .product-card .sharebar {{
            font-size: 12px;
            color: #4caf50;
            word-break: break-all;
        }}
        .product-card .sharebar.no {{
            color: #f44336;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin-top: 4px;
        }}
        .badge.success {{ background: #e8f5e9; color: #2e7d32; }}
        .badge.fail {{ background: #ffebee; color: #c62828; }}
        
        /* 表格模式 */
        .table-mode {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            margin-top: 30px;
        }}
        .table-mode table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        .table-mode th {{
            background: #1a237e;
            color: white;
            padding: 12px 16px;
            text-align: left;
        }}
        .table-mode td {{
            padding: 10px 16px;
            border-bottom: 1px solid #eee;
        }}
        .table-mode tr:hover td {{ background: #f5f7fa; }}
        .table-mode .no-data {{ color: #999; font-style: italic; }}
        
        /* 模式切换 */
        .mode-toggle {{
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
        }}
        .mode-toggle button {{
            padding: 8px 24px;
            border: 2px solid #1a237e;
            background: white;
            color: #1a237e;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
        }}
        .mode-toggle button.active {{
            background: #1a237e;
            color: white;
        }}
        .mode-toggle button:hover {{
            transform: scale(1.02);
        }}
        
        /* 响应式 */
        @media (max-width: 600px) {{
            body {{ padding: 12px; }}
            .product-grid {{ grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }}
            .header h1 {{ font-size: 22px; }}
            .stats {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        
        /* 打印样式 */
        @media print {{
            body {{ background: white; padding: 10px; }}
            .product-card {{ box-shadow: none; border: 1px solid #ddd; }}
            .mode-toggle {{ display: none; }}
            .product-card:hover {{ transform: none; box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>🛍️ 安利日本产品目录</h1>
            <div class="sub">{category_name} · 共 {total} 个产品 · 生成时间: {datetime}</div>
        </div>
        
        <!-- 统计 -->
        <div class="stats">
            <div class="stat-card">
                <div class="num">{total}</div>
                <div class="label">📦 产品总数</div>
            </div>
            <div class="stat-card" style="border-left: 4px solid #4caf50;">
                <div class="num" style="color: #2e7d32;">{with_sharebar}</div>
                <div class="label">✅ 有 Sharebar</div>
            </div>
            <div class="stat-card" style="border-left: 4px solid #f44336;">
                <div class="num" style="color: #c62828;">{without_sharebar}</div>
                <div class="label">❌ 无 Sharebar</div>
            </div>
        </div>
        
        <!-- 模式切换 -->
        <div class="mode-toggle">
            <button class="active" onclick="showMode('grid')">📊 网格视图</button>
            <button onclick="showMode('table')">📋 表格视图</button>
        </div>
        
        <!-- 网格视图 -->
        <div id="grid-view" class="product-grid">
            {product_cards}
        </div>
        
        <!-- 表格视图 -->
        <div id="table-view" class="table-mode" style="display:none;">
            <table>
                <thead>
                    <tr>
                        <th>序号</th>
                        <th>产品ID</th>
                        <th>产品名称</th>
                        <th>Sharebar状态</th>
                        <th>链接</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function showMode(mode) {{
            document.querySelectorAll('.mode-toggle button').forEach(b => b.classList.remove('active'));
            document.getElementById('grid-view').style.display = mode === 'grid' ? 'grid' : 'none';
            document.getElementById('table-view').style.display = mode === 'table' ? 'block' : 'none';
            if (mode === 'grid') {{
                document.querySelector('.mode-toggle button:first-child').classList.add('active');
            }} else {{
                document.querySelector('.mode-toggle button:last-child').classList.add('active');
            }}
        }}
    </script>
</body>
</html>
    '''
    
    def export_products(self, products: List[Dict], output_path: Path,
                        category_name: str = "全产品") -> bool:
        """导出产品数据为HTML"""
        try:
            total = len(products)
            with_sharebar = sum(1 for p in products if p.get('has_sharebar', False))
            without_sharebar = total - with_sharebar
            
            # 生成产品卡片
            product_cards = self._generate_cards(products)
            table_rows = self._generate_table_rows(products)
            
            html = self.TEMPLATE.format(
                category_name=category_name,
                total=total,
                with_sharebar=with_sharebar,
                without_sharebar=without_sharebar,
                datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                product_cards=product_cards,
                table_rows=table_rows
            )
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            print(f"✅ HTML已生成: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ HTML导出失败: {e}")
            return False
    
    def _generate_cards(self, products: List[Dict]) -> str:
        """生成产品卡片HTML"""
        cards = []
        for p in products:
            image_html = ''
            merged_path = p.get('merged_path')
            if merged_path and Path(merged_path).exists():
                image_html = f'<img class="image" src="{Path(merged_path).name}" alt="{p.get("name", "")}">'
            elif p.get('image_path') and Path(p['image_path']).exists():
                image_html = f'<img class="image" src="{Path(p["image_path"]).name}" alt="{p.get("name", "")}">'
            else:
                image_html = '<div class="image" style="display:flex;align-items:center;justify-content:center;color:#ccc;">无图片</div>'
            
            sharebar_status = (
                f'<span class="badge success">✅ 有Sharebar</span>'
                if p.get('has_sharebar') else
                f'<span class="badge fail">❌ 无Sharebar</span>'
            )
            
            sharebar_link = p.get('sharebar', '')
            if sharebar_link:
                sharebar_html = f'<div class="sharebar">🔗 {sharebar_link[:50]}...</div>'
            else:
                sharebar_html = '<div class="sharebar no">无分享链接</div>'
            
            card = f'''
            <div class="product-card">
                {image_html}
                <div class="info">
                    <div class="id">#{p.get("product_id", "")}</div>
                    <div class="name">{p.get("name", "未知产品")}</div>
                    {sharebar_status}
                    {sharebar_html}
                </div>
            </div>
            '''
            cards.append(card)
        
        return '\n'.join(cards)
    
    def _generate_table_rows(self, products: List[Dict]) -> str:
        """生成表格行HTML"""
        rows = []
        for idx, p in enumerate(products, 1):
            link = p.get('sharebar', p.get('url', ''))[:60]
            row = f'''
            <tr>
                <td>{idx}</td>
                <td>{p.get("product_id", "")}</td>
                <td>{p.get("name", "未知产品")}</td>
                <td>{"✅ 有" if p.get("has_sharebar") else "❌ 无"}</td>
                <td class="no-data">{link if link else "无"}</td>
            </tr>
            '''
            rows.append(row)
        return '\n'.join(rows)