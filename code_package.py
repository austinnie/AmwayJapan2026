"""
项目打包脚本 - 将整个项目打包为 7z 压缩包
需要安装 7-Zip 或使用 Python 的 shutil 打包
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置
# ============================================================

# 要排除的目录
EXCLUDE_DIRS = [
    '__pycache__',
    '.git',
    '.idea', 
    '.vscode',
    'node_modules',
    'venv', '.venv', 'env', '.env',
    '.pytest_cache', '.mypy_cache', '.ruff_cache',
    'output',  # 输出目录可能很大
    'logs',    # 日志目录
]

# 要排除的文件
EXCLUDE_FILES = [
    '.DS_Store',
    'Thumbs.db',
    'desktop.ini',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '*.log',
    '*.7z',
    '*.zip',
    '*.rar',
    'collected_code.txt',  # 排除收集的代码文件本身
]

# 压缩包名称
ARCHIVE_NAME = "AmwayJapan2026"

# 7-Zip 路径（Windows 通常在这里）
_7Z_PATH = r"C:\Program Files\7-Zip\7z.exe"


# ============================================================
# 主函数
# ============================================================

def find_7z():
    """查找 7z.exe 路径"""
    paths = [
        _7Z_PATH,
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    
    for p in paths:
        if os.path.exists(p):
            return p
    
    # 尝试在 PATH 中查找
    for p in os.environ.get("PATH", "").split(";"):
        try:
            test_path = os.path.join(p, "7z.exe")
            if os.path.exists(test_path):
                return test_path
        except:
            continue
    
    return None


def get_exclude_args(excludes):
    """生成 7z 排除参数"""
    args = []
    for item in excludes:
        args.extend(["-xr!" + item])
    return args


def pack_with_7z(root_dir: Path, output_path: Path):
    """使用 7-Zip 打包"""
    seven_zip = find_7z()
    if not seven_zip:
        print("❌ 未找到 7-Zip (7z.exe)")
        print("   请安装 7-Zip 或修改 _7Z_PATH 变量")
        print("   下载地址: https://www.7-zip.org/")
        return False
    
    print(f"📦 使用 7-Zip: {seven_zip}")
    print(f"📂 打包目录: {root_dir}")
    print(f"📄 输出文件: {output_path}")
    print("-" * 60)
    
    # 构建命令
    cmd = [
        seven_zip,
        "a",
        "-t7z",
        "-mx=9",           # 最大压缩
        "-mmt=on",         # 多线程
        f"-o{output_path.parent}",  # 输出目录
        str(output_path),  # 输出文件
        ".",               # 当前目录
    ]
    
    # 添加排除参数
    for pattern in EXCLUDE_DIRS:
        cmd.append(f"-xr!{pattern}")
    for pattern in EXCLUDE_FILES:
        cmd.append(f"-xr!{pattern}")
    
    # 执行
    try:
        # 切换到项目目录
        os.chdir(root_dir)
        
        print("⏳ 正在压缩，请稍候...")
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            size = output_path.stat().st_size
            print(f"✅ 打包成功: {output_path}")
            print(f"📊 压缩包大小: {size / (1024*1024):.2f} MB")
            return True
        else:
            print(f"❌ 打包失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 打包失败: {e}")
        return False


def pack_with_shutil(root_dir: Path, output_path: Path):
    """使用 shutil 打包为 zip（备用方案）"""
    print(f"📂 打包目录: {root_dir}")
    print(f"📄 输出文件: {output_path}")
    print("-" * 60)
    
    # 改为 zip 格式
    zip_path = output_path.with_suffix('.zip')
    
    # 构建排除函数
    def should_exclude(file_path):
        rel_path = file_path.relative_to(root_dir)
        parts = rel_path.parts
        
        # 检查目录排除
        for excluded in EXCLUDE_DIRS:
            if excluded in parts:
                return True
        
        # 检查文件排除
        for pattern in EXCLUDE_FILES:
            if pattern.startswith('*.'):
                if file_path.suffix == pattern[1:]:
                    return True
            if file_path.name == pattern:
                return True
        
        return False
    
    # 收集文件
    files_to_pack = []
    total_size = 0
    
    for file_path in root_dir.rglob('*'):
        if file_path.is_dir():
            continue
        if should_exclude(file_path):
            continue
        files_to_pack.append(file_path)
        total_size += file_path.stat().st_size
    
    print(f"📊 找到 {len(files_to_pack)} 个文件，总大小 {total_size / (1024*1024):.2f} MB")
    print("⏳ 正在压缩，请稍候...")
    
    # 创建 zip
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for i, file_path in enumerate(files_to_pack):
                if i % 50 == 0:
                    print(f"  进度: {i}/{len(files_to_pack)}")
                arcname = file_path.relative_to(root_dir)
                zipf.write(file_path, arcname)
        
        size = zip_path.stat().st_size
        print(f"✅ 打包成功: {zip_path}")
        print(f"📊 压缩包大小: {size / (1024*1024):.2f} MB")
        return True
        
    except Exception as e:
        print(f"❌ 打包失败: {e}")
        return False


def main():
    root_dir = Path(__file__).parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{ARCHIVE_NAME}_{timestamp}"
    
    output_path = root_dir / f"{archive_name}.7z"
    
    print("=" * 60)
    print("  项目打包工具")
    print("=" * 60)
    print()
    
    # 检查当前目录
    print(f"📁 当前项目: {root_dir}")
    
    # 优先使用 7-Zip
    if find_7z():
        success = pack_with_7z(root_dir, output_path)
    else:
        print("⚠️ 未找到 7-Zip，使用 Python zipfile 打包")
        import zipfile
        success = pack_with_shutil(root_dir, output_path)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 打包完成!")
        print("=" * 60)
    else:
        print("\n❌ 打包失败")


if __name__ == "__main__":
    main()