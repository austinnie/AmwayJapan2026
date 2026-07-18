# handlers/html_handler.py
"""
HTML导出模块 - 生成美观的产品展示页面
"""
from pathlib import Path
from typing import List, Dict
from datetime import datetime


# handlers/html_handler.py

class HTMLHandler:
    """HTML处理器"""
    
    # ============================================================
    # 路径配置
    # ============================================================
    
    IMG_SRC_PREFIX = "../products/all/merged_images/"
    IMG_SRC_PREFIX_ORIGINAL = "../products/all/product_images/"
    
    # ============================================================
    # 微信公众号适配模板（1列布局）
    # ============================================================
    
    TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>安利日本产品目录 - {category_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
            background: #f5f6fa;
            padding: 12px;
            color: #333;
            font-size: 15px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 640px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 16px;
            padding: 20px 16px 30px;
            box-shadow: 0 2px 16px rgba(0,0,0,0.06);
        }}
        
        /* ===== 头部 ===== */
        .header {{
            text-align: center;
            padding: 16px 0 14px;
            border-bottom: 3px solid #e8edf5;
            margin-bottom: 18px;
        }}
        .header h1 {{
            font-size: 24px;
            font-weight: 700;
            color: #1a237e;
            letter-spacing: 3px;
        }}
        .header .sub {{
            font-size: 13px;
            color: #999;
            margin-top: 4px;
        }}
        
        /* ===== 统计卡片 ===== */
        .stats {{
            display: flex;
            justify-content: space-around;
            background: linear-gradient(135deg, #f5f8ff, #eef3fc);
            border-radius: 12px;
            padding: 14px 0;
            margin-bottom: 18px;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-item .num {{
            font-size: 26px;
            font-weight: 700;
            color: #1a237e;
        }}
        .stat-item .label {{
            font-size: 12px;
            color: #888;
        }}
        .stat-item .num.green {{ color: #2e7d32; }}
        .stat-item .num.red {{ color: #c62828; }}
        
        /* ===== 模式切换 ===== */
        .mode-toggle {{
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
            justify-content: center;
        }}
        .mode-toggle button {{
            flex: 1;
            max-width: 140px;
            padding: 8px 0;
            border: 2px solid #1a237e;
            background: #fff;
            color: #1a237e;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.25s;
        }}
        .mode-toggle button.active {{
            background: #1a237e;
            color: #fff;
        }}
        
        /* ===== 产品列表（1列） ===== */
        .product-list {{
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}
        
        .product-card {{
            display: flex;
            background: #fafbfc;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #eef1f5;
            transition: all 0.2s;
            align-items: stretch;
        }}
        .product-card:hover {{
            border-color: #1a237e;
            box-shadow: 0 4px 16px rgba(26,35,126,0.10);
        }}
        
        /* 图片区域 - 固定宽度正方形 */
        .product-card .image-wrap {{
            flex: 0 0 120px;
            width: 120px;
            height: 120px;
            background: #f7f8fa;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .product-card .image-wrap img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            padding: 6px;
            background: #ffffff;
        }}
        
        /* 信息区域 */
        .product-card .info {{
            flex: 1;
            padding: 10px 14px 10px 12px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-width: 0;
        }}
        .product-card .id {{
            font-size: 11px;
            color: #bbb;
            font-weight: 500;
        }}
        .product-card .name {{
            font-size: 15px;
            font-weight: 600;
            color: #1a237e;
            margin: 2px 0 4px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .product-card .badge {{
            display: inline-block;
            padding: 1px 10px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 600;
            width: fit-content;
        }}
        .product-card .badge.success {{
            background: #e8f5e9;
            color: #2e7d32;
        }}
        .product-card .badge.fail {{
            background: #ffebee;
            color: #c62828;
        }}
        
        .product-card .sharebar {{
            font-size: 11px;
            color: #4caf50;
            word-break: break-all;
            margin-top: 4px;
            background: #f0f2f5;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: "SF Mono", monospace;
        }}
        .product-card .sharebar.no {{
            color: #ccc;
        }}
        
        /* ===== 表格 ===== */
        .table-wrap {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            margin-top: 16px;
            border-radius: 12px;
            border: 1px solid #eef1f5;
        }}
        .table-wrap table {{
            width: 100%;
            min-width: 400px;
            border-collapse: collapse;
            font-size: 12px;
        }}
        .table-wrap th {{
            background: #1a237e;
            color: #fff;
            padding: 8px 12px;
            text-align: left;
            font-weight: 600;
        }}
        .table-wrap td {{
            padding: 7px 12px;
            border-bottom: 1px solid #eee;
            color: #444;
        }}
        .table-wrap tr:nth-child(even) td {{
            background: #fafbfc;
        }}
        .table-wrap .no-data {{ color: #bbb; }}
        
        /* ===== 底部 ===== */
        .footer {{
            text-align: center;
            margin-top: 20px;
            padding-top: 14px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #ccc;
        }}
        
        /* ===== 响应式 ===== */
        @media (max-width: 480px) {{
            body {{ padding: 8px; }}
            .container {{ padding: 12px 10px 20px; border-radius: 12px; }}
            .header h1 {{ font-size: 18px; }}
            
            .product-card .image-wrap {{
                flex: 0 0 90px;
                width: 90px;
                height: 90px;
            }}
            .product-card .info {{ padding: 8px 10px; }}
            .product-card .name {{ font-size: 13px; }}
            .stats .num {{ font-size: 20px; }}
            .product-card .sharebar {{ font-size: 10px; }}
        }}
        
        @media print {{
            body {{ background: #fff; padding: 0; }}
            .container {{ box-shadow: none; border-radius: 0; }}
            .mode-toggle {{ display: none; }}
            .product-card {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>🛍️ 安利日本产品目录</h1>
            <div class="sub">{category_name} · 共 {total} 个产品 · {datetime}</div>
        </div>
        
        <!-- 统计 -->
        <div class="stats">
            <div class="stat-item">
                <div class="num">{total}</div>
                <div class="label">📦 产品总数</div>
            </div>
            <div class="stat-item">
                <div class="num green">{with_sharebar}</div>
                <div class="label">✅ 有 Sharebar</div>
            </div>
            <div class="stat-item">
                <div class="num red">{without_sharebar}</div>
                <div class="label">❌ 无 Sharebar</div>
            </div>
        </div>
        
        <!-- 模式切换 -->
        <div class="mode-toggle">
            <button class="active" onclick="showMode('list')">📱 列表</button>
            <button onclick="showMode('table')">📋 表格</button>
        </div>
        
        <!-- 列表视图（1列） -->
        <div id="list-view" class="product-list">
            {product_cards}
        </div>
        
        <!-- 表格视图 -->
        <div id="table-view" class="table-wrap" style="display:none;">
            <table>
                <thead>
                    <tr><th>#</th><th>产品ID</th><th>名称</th><th>状态</th></tr>
                </thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
        
        <div class="footer">安利日本 · 产品目录 · 共 {total} 个产品</div>
    </div>
    
    <script>
        function showMode(mode) {{
            const btns = document.querySelectorAll('.mode-toggle button');
            btns.forEach(b => b.classList.remove('active'));
            const list = document.getElementById('list-view');
            const table = document.getElementById('table-view');
            if (mode === 'list') {{
                list.style.display = 'flex';
                table.style.display = 'none';
                btns[0].classList.add('active');
            }} else {{
                list.style.display = 'none';
                table.style.display = 'block';
                btns[1].classList.add('active');
            }}
        }}
    </script>
</body>
</html>
    '''
    # ============================================================
    # 导出方法
    # ============================================================
    
    def export_products(self, products: List[Dict], output_path: Path,
                        category_name: str = "全产品", silent: bool = False) -> bool:
        """导出产品数据为HTML"""
        try:
            total = len(products)
            with_sharebar = sum(1 for p in products if p.get('has_sharebar', False))
            without_sharebar = total - with_sharebar
            
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
            
            if not silent:
                print(f"✅ HTML已生成: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ HTML导出失败: {e}")
            return False
    
    # ============================================================
    # 生成卡片
    # ============================================================
    
    def _generate_cards(self, products: List[Dict]) -> str:
        """生成产品卡片HTML"""
        cards = []
        for p in products:
            product_id = p.get('product_id', '') or ''
            name = p.get('name', '未知产品') or '未知产品'
            sharebar = p.get('sharebar', '') or ''
            
            # 🔑 使用配置的图片路径
            merged_path = p.get('merged_path')
            if merged_path and Path(merged_path).exists():
                image_filename = Path(merged_path).name
                image_html = f'<img class="image" src="{self.IMG_SRC_PREFIX}{image_filename}" alt="{name}">'
            else:
                image_path = p.get('image_path')
                if image_path and Path(image_path).exists():
                    image_filename = Path(image_path).name
                    image_html = f'<img class="image" src="{self.IMG_SRC_PREFIX_ORIGINAL}{image_filename}" alt="{name}">'
                else:
                    image_html = '<div class="image" style="display:flex;align-items:center;justify-content:center;color:#ccc;">无图片</div>'
            
            sharebar_status = (
                f'<span class="badge success">✅ 有Sharebar</span>'
                if p.get('has_sharebar') else
                f'<span class="badge fail">❌ 无Sharebar</span>'
            )
            
            if sharebar:
                sharebar_html = f'<div class="sharebar">🔗 {sharebar[:50]}...</div>'
            else:
                sharebar_html = '<div class="sharebar no">无分享链接</div>'
            
            card = f'''
            <div class="product-card">
                {image_html}
                <div class="info">
                    <div class="id">#{product_id}</div>
                    <div class="name">{name}</div>
                    {sharebar_status}
                    {sharebar_html}
                </div>
            </div>
            '''
            cards.append(card)
        
        return '\n'.join(cards)
    
    # ============================================================
    # 生成表格行
    # ============================================================
    
    def _generate_table_rows(self, products: List[Dict]) -> str:
        """生成表格行HTML"""
        rows = []
        for idx, p in enumerate(products, 1):
            product_id = p.get('product_id', '') or ''
            name = p.get('name', '未知产品') or '未知产品'
            link = p.get('sharebar', p.get('url', '')) or ''
            link = link[:60] if link else '无'
            has_sharebar = p.get('has_sharebar', False)
            
            row = f'''
            <tr>
                <td>{idx}</td>
                <td>{product_id}</td>
                <td>{name}</td>
                <td>{"✅ 有" if has_sharebar else "❌ 无"}</td>
                <td class="no-data">{link}</td>
            </tr>
            '''
            rows.append(row)
        return '\n'.join(rows)