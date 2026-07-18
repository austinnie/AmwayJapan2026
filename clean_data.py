# clean_data.py
"""清理旧数据，准备重新运行"""
import shutil
from pathlib import Path

def clean():
    base_dir = Path(__file__).parent
    
    # 要删除的目录
    dirs_to_delete = [
        base_dir / "products" / "all",
        base_dir / "output" / "images",
    ]
    
    # 要删除的文件
    files_to_delete = [
        base_dir / "output" / "processed_products.json",
        base_dir / "output" / "安利日本产品目录.html",
        base_dir / "output" / "安利日本产品目录.pdf",
        base_dir / "output" / "有Sharebar产品.html",
        base_dir / "output" / "有Sharebar产品.pdf",
        base_dir / "output" / "无Sharebar产品.html",
        base_dir / "output" / "无Sharebar产品.pdf",
        base_dir / "products" / "list-withsharebar.txt",
        base_dir / "products" / "list-withoutsharebar.txt",
    ]
    
    # 删除目录
    for d in dirs_to_delete:
        if d.exists():
            shutil.rmtree(d)
            print(f"🗑️ 已删除目录: {d}")
    
    # 删除文件
    for f in files_to_delete:
        if f.exists():
            f.unlink()
            print(f"🗑️ 已删除文件: {f}")
    
    print("\n✅ 清理完成！可以重新运行 main.py")

if __name__ == "__main__":
    clean()