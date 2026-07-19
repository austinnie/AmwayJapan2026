# clean_qr_codes.py
"""
清理二维码文件：删除 product_images 中不存在的产品编号对应的二维码
"""
import os
from pathlib import Path

def clean_qr_codes():
    """清理不存在的产品编号对应的二维码"""
    
    # 设置路径 - 根据你的实际目录结构调整
    base_dir = Path(".")  # 当前目录，或者指定你的 products/all 目录
    product_images_dir = base_dir / "product_images"
    qr_codes_dir = base_dir / "qr_codes"
    
    if not product_images_dir.exists():
        print(f"❌ product_images 目录不存在: {product_images_dir}")
        return
    
    if not qr_codes_dir.exists():
        print(f"❌ qr_codes 目录不存在: {qr_codes_dir}")
        return
    
    # 获取 product_images 中所有产品编号（去掉扩展名）
    product_ids = set()
    for f in product_images_dir.glob("*.png"):
        product_ids.add(f.stem)  # stem 是不带扩展名的文件名
    
    print(f"📊 product_images 中有 {len(product_ids)} 个产品")
    
    # 遍历 qr_codes 目录
    deleted_count = 0
    kept_count = 0
    
    for qr_file in qr_codes_dir.glob("*_qr.png"):
        # 提取产品编号（去掉 _qr 后缀）
        product_id = qr_file.stem.replace("_qr", "")
        
        if product_id not in product_ids:
            # 产品编号不在 product_images 中，删除
            try:
                qr_file.unlink()
                deleted_count += 1
                print(f"🗑️ 删除: {qr_file.name} (产品编号: {product_id})")
            except Exception as e:
                print(f"❌ 删除失败: {qr_file.name} - {e}")
        else:
            kept_count += 1
    
    print("\n" + "=" * 50)
    print(f"✅ 清理完成!")
    print(f"   保留: {kept_count} 个二维码")
    print(f"   删除: {deleted_count} 个二维码")
    print("=" * 50)


def clean_qr_codes_dry_run():
    """预览模式：只显示会删除哪些文件，不实际删除"""
    
    base_dir = Path(".")  # 根据实际情况修改
    product_images_dir = base_dir / "product_images"
    qr_codes_dir = base_dir / "qr_codes"
    
    if not product_images_dir.exists():
        print(f"❌ product_images 目录不存在: {product_images_dir}")
        return
    
    if not qr_codes_dir.exists():
        print(f"❌ qr_codes 目录不存在: {qr_codes_dir}")
        return
    
    product_ids = set()
    for f in product_images_dir.glob("*.png"):
        product_ids.add(f.stem)
    
    print(f"📊 product_images 中有 {len(product_ids)} 个产品")
    print("\n📋 将删除以下二维码文件:")
    
    to_delete = []
    for qr_file in qr_codes_dir.glob("*_qr.png"):
        product_id = qr_file.stem.replace("_qr", "")
        if product_id not in product_ids:
            to_delete.append(qr_file)
            print(f"   🗑️ {qr_file.name} (产品编号: {product_id})")
    
    print(f"\n共 {len(to_delete)} 个文件将被删除")
    return to_delete


if __name__ == "__main__":
    import sys
    
    if "--dry-run" in sys.argv or "-n" in sys.argv:
        print("🔍 预览模式 (不会实际删除)\n")
        clean_qr_codes_dry_run()
    else:
        print("🧹 开始清理二维码文件...\n")
        confirm = input("确认删除 product_images 中不存在的产品编号对应的二维码？(y/n): ")
        if confirm.lower() == 'y':
            clean_qr_codes()
        else:
            print("已取消")