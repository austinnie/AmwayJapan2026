# 🛍️ 安利日本产品自动化系统

基于 Playwright 的安利日本产品自动化处理工具，支持产品扫描、Sharebar 链接获取、二维码生成、多格式文档导出（HTML/PDF/Word），并提供图形界面。

---

## ✨ 功能特性

### 核心功能
- ✅ **自动登录** - 自动登录安利日本网站
- ✅ **产品扫描** - 批量扫描产品，获取名称、图片、Sharebar 链接
- ✅ **智能分类** - 自动分类有/无 Sharebar 的产品
- ✅ **二维码生成** - 为每个产品生成二维码（Sharebar 或产品 URL）
- ✅ **图片合并** - 产品图片与二维码自动合并
- ✅ **断点续传** - 支持中断后继续，不重复处理

### 导出功能
- 📄 **HTML 导出** - 美观的响应式产品目录（适配微信公众号）
- 📄 **PDF 导出** - 高质量可打印文档
- 📄 **Word 导出** - 可编辑的产品目录文档

### 界面
- 🖥️ **命令行界面 (CLI)** - 适合服务器/自动化场景
- 🖥️ **图形界面 (GUI)** - PySide6 现代界面，操作直观

### 运行模式
| 模式 | 说明 |
|------|------|
| `full` | 完整流程（扫描 + 二维码 + 导出） |
| `scan` | 仅扫描产品，获取图片和 Sharebar |
| `export` | 仅导出文档（无需浏览器） |
| `fetch` | 从网站获取产品列表 |

---

## 📁 项目结构
AmwayJapan2026/
├── core/
│ ├── browser.py # 浏览器管理
│ ├── login.py # 登录模块
│ └── product_processor.py # 核心处理器
├── handlers/
│ ├── sharebar_handler.py # Sharebar 获取
│ ├── image_handler.py # 图片处理
│ ├── qr_handler.py # 二维码生成
│ ├── html_handler.py # HTML 导出
│ ├── pdf_handler.py # PDF 导出
│ └── word_handler.py # Word 导出
├── utils/
│ ├── file_utils.py # 文件工具
│ ├── logger.py # 日志模块
│ └── progress_manager.py # 进度管理（断点续传）
├── products/ # 产品数据目录
│ ├── all/
│ │ ├── product_images/ # 产品截图
│ │ ├── qr_codes/ # 二维码
│ │ └── merged_images/ # 合并图
│ ├── exports/ # 导出文档
│ │ ├── 安利日本产品目录.html
│ │ ├── 安利日本产品目录.pdf
│ │ └── 安利日本产品目录.docx
│ ├── list-all.txt # 产品列表（输入）
│ ├── list-withsharebar.txt # 有 Sharebar 的产品
│ ├── list-withoutsharebar.txt # 无 Sharebar 的产品
│ ├── product_names.json # 产品名称映射
│ ├── sharebar_mapping.json # Sharebar 映射
│ ├── processed_products.json # 扫描进度
│ └── qr_progress.json # 二维码进度
├── logs/
│ └── app.log # 运行日志
├── config.py # 配置文件
├── main.py # CLI 入口
├── gui_pyside.py # GUI 入口
├── requirements.txt
└── README.md

---

## 🚀 安装与配置

### 1. 环境要求
- Python 3.8+
- Windows / macOS / Linux

### 2. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
3. 配置文件
编辑 config.py 修改登录信息：
# config.py
LOGIN_URL = "https://idp.amwaylive.com/..."  # 登录 URL
USERNAME = "your_email@example.com"          # 用户名
PASSWORD = "your_password"                   # 密码
4. 准备产品列表
在 products/list-all.txt 中添加产品 URL（每行一个）：
https://www.amwaylive.com/jp/products/1179
https://www.amwaylive.com/jp/products/1634
...


🎮 使用方式
CLI 命令行模式
# 完整流程
python main.py --mode full

# 仅扫描
python main.py --mode scan

# 仅导出文档（无需浏览器，即使网站维护也能用）
python main.py --mode export

# 获取产品列表
python main.py --mode fetch

# 无头模式（不显示浏览器）
python main.py --mode scan --headless

GUI 图形界面模式
python gui_pyside.py

界面功能：

选择运行模式（完整流程 / 仅扫描 / 仅导出 / 获取列表）

无头模式开关

实时彩色日志显示

进度条展示

打开输出目录

重置进度


📋 数据文件说明

文件	说明
list-all.txt	输入：产品 URL 列表
list-withsharebar.txt	输出：有 Sharebar 的产品 URL
list-withoutsharebar.txt	输出：无 Sharebar 的产品 URL
product_names.json	产品名称映射 {product_id: name}
sharebar_mapping.json	Sharebar 映射 {product_id: sharebar_url}
processed_products.json	已扫描产品 ID 列表（断点续传）
qr_progress.json	已生成二维码的产品 ID 列表（断点续传）


🔧 常见问题

Q: 网站维护时怎么办？
程序会自动检测维护状态，提示后退出，不会浪费时间等待登录超时。
--mode export 模式不依赖网站，维护期间仍可正常导出文档。

Q: 扫描中断了怎么办？
支持断点续传，重新运行会自动跳过已处理的产品。

Q: 产品名称提取不正确？
程序会从页面标题、meta 标签、h1 标签多个来源提取，并自动清理网站名称后缀。

Q: PDF 导出失败？
程序支持三种转换方式，会自动尝试：

Playwright（推荐）

wkhtmltopdf（需要安装）

weasyprint（需要安装）

Q: 二维码用的是什么 URL？
有 Sharebar → 使用 Sharebar 链接

无 Sharebar → 使用产品 URL（降级方案）



📦 依赖清单
playwright>=1.40.0      # 浏览器自动化
pillow>=10.0.0          # 图片处理
qrcode>=7.4.0           # 二维码生成
python-docx>=1.1.0      # Word 导出
pyperclip>=1.8.0        # 剪贴板操作
beautifulsoup4>=4.12.0  # HTML 解析
lxml>=4.9.0             # HTML 解析加速
aiohttp>=3.9.0          # 异步 HTTP
PySide6>=6.6.0          # GUI 界面（可选）


🎯 工作流程

┌─────────────────────────────────────────────────────────────┐
│  第一步：扫描产品                                          │
│  ├── 读取 list-all.txt                                    │
│  ├── 逐个访问产品页面                                      │
│  ├── 提取产品名称 → 保存到 product_names.json             │
│  ├── 截图产品图片 → products/all/product_images/          │
│  ├── 获取 Sharebar → 保存到 sharebar_mapping.json         │
│  └── 分类保存到 list-withsharebar.txt / list-withoutsharebar.txt │
├─────────────────────────────────────────────────────────────┤
│  第二步：二次确认（可选）                                   │
│  └── 对无 Sharebar 的产品重新尝试 3 次                     │
├─────────────────────────────────────────────────────────────┤
│  第三步：生成二维码并合并图片                               │
│  ├── 读取 list-withsharebar.txt / list-withoutsharebar.txt │
│  ├── 生成二维码 → products/all/qr_codes/                  │
│  └── 合并图片 → products/all/merged_images/               │
├─────────────────────────────────────────────────────────────┤
│  第四步：导出文档                                          │
│  ├── HTML → products/exports/xxx.html                     │
│  ├── PDF  → products/exports/xxx.pdf                     │
│  └── Word → products/exports/xxx.docx                    │
└─────────────────────────────────────────────────────────────┘

📝 License
MIT License

🤝 贡献
欢迎提交 Issue 和 Pull Request。

Made with ❤️ for Amway Japan product automation
