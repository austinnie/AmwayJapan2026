"""
代码收集脚本 - 将项目所有代码文件的内容收集到一个文件中
方便分享给他人或AI分析
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置
# ============================================================

# 要收集的文件扩展名
INCLUDE_EXTENSIONS = {
    '.py', '.txt', '.md', '.json', '.yml', '.yaml', '.toml',
    '.html', '.css', '.js', '.xml', '.csv'
}

# 要排除的目录
EXCLUDE_DIRS = {
    '__pycache__', '.git', '.idea', '.vscode', 
    'node_modules', 'venv', '.venv', 'env', '.env',
    '.pytest_cache', '.mypy_cache', '.ruff_cache'
}

# 要排除的文件
EXCLUDE_FILES = {
    '.DS_Store', 'Thumbs.db', 'desktop.ini',
    'sharebar_debug.png', 'login_failed.png'
}

# 输出文件名
OUTPUT_FILE = "collected_code.txt"


# ============================================================
# 主函数
# ============================================================

def collect_code(root_dir: Path, output_file: Path):
    """收集所有代码文件的内容"""
    
    print(f"📂 扫描目录: {root_dir}")
    print(f"📄 输出文件: {output_file}")
    print("-" * 60)
    
    # 收集所有文件
    all_files = []
    total_size = 0
    
    for file_path in root_dir.rglob('*'):
        # 跳过目录
        if file_path.is_dir():
            continue
        
        # 检查是否在排除目录中
        if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
            continue
        
        # 检查扩展名
        if file_path.suffix not in INCLUDE_EXTENSIONS:
            continue
        
        # 检查排除文件
        if file_path.name in EXCLUDE_FILES:
            continue
        
        all_files.append(file_path)
        total_size += file_path.stat().st_size
    
    print(f"📊 找到 {len(all_files)} 个文件，总大小: {total_size / 1024:.1f} KB")
    print("-" * 60)
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as out_f:
        # 写入头部
        out_f.write("=" * 80 + "\n")
        out_f.write(f"  代码收集 - 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out_f.write(f"  项目目录: {root_dir}\n")
        out_f.write(f"  文件总数: {len(all_files)}\n")
        out_f.write("=" * 80 + "\n\n")
        
        # 按扩展名分组显示
        ext_count = {}
        for f in all_files:
            ext = f.suffix or 'no_ext'
            ext_count[ext] = ext_count.get(ext, 0) + 1
        
        out_f.write("📊 文件类型统计:\n")
        for ext, count in sorted(ext_count.items(), key=lambda x: -x[1]):
            out_f.write(f"   {ext}: {count} 个\n")
        out_f.write("\n" + "-" * 80 + "\n\n")
        
        # 逐个写入文件内容
        for i, file_path in enumerate(all_files, 1):
            try:
                # 相对路径
                rel_path = file_path.relative_to(root_dir)
                
                # 写入文件头
                out_f.write(f"\n{'='*80}\n")
                out_f.write(f"文件: {rel_path}\n")
                out_f.write(f"大小: {file_path.stat().st_size} 字节\n")
                out_f.write(f"{'='*80}\n\n")
                
                # 读取并写入文件内容
                try:
                    content = file_path.read_text(encoding='utf-8')
                    out_f.write(content)
                except UnicodeDecodeError:
                    # 尝试其他编码
                    try:
                        content = file_path.read_text(encoding='gbk')
                        out_f.write(content)
                    except:
                        out_f.write(f"[无法解码: 二进制或非文本文件]\n")
                
                out_f.write(f"\n\n")
                
                # 进度显示
                if i % 10 == 0:
                    print(f"  已处理: {i}/{len(all_files)}")
                    
            except Exception as e:
                out_f.write(f"\n[错误: 无法读取文件 - {e}]\n\n")
        
        # 写入统计信息
        out_f.write("\n" + "=" * 80 + "\n")
        out_f.write(f"  收集完成\n")
        out_f.write(f"  文件总数: {len(all_files)}\n")
        out_f.write(f"  总大小: {total_size / 1024:.1f} KB\n")
        out_f.write(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out_f.write("=" * 80 + "\n")
    
    print("-" * 60)
    print(f"✅ 代码收集完成: {output_file}")
    print(f"📊 共收集 {len(all_files)} 个文件，总大小 {total_size / 1024:.1f} KB")


# ============================================================
# 命令行入口
# ============================================================

def main():
    # 默认收集当前目录
    root_dir = Path(__file__).parent
    
    # 可指定收集目录
    if len(sys.argv) > 1:
        root_dir = Path(sys.argv[1])
        if not root_dir.exists():
            print(f"❌ 目录不存在: {root_dir}")
            return
    
    output_file = root_dir / OUTPUT_FILE
    
    collect_code(root_dir, output_file)


if __name__ == "__main__":
    main()