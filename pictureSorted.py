import os
import tkinter as tk
from tkinter import ttk, scrolledtext
from PIL import Image
from datetime import datetime
import piexif
import glob
from pathlib import Path

def get_photo_creation_date(photo_path):
    """获取照片的拍摄时间（修复版）"""
    try:
        image = Image.open(photo_path)
        
        # 1. 检查是否存在EXIF数据
        exif_data = image.info.get("exif")
        if exif_data:  # 只有当EXIF数据存在且非空时才处理
            try:
                # 2. 确保exif_data是字节类型
                if isinstance(exif_data, bytes) and len(exif_data) > 0:
                    exif_dict = piexif.load(exif_data)
                    if "Exif" in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
                        date_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode()
                        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            except (piexif.InvalidImageDataError, ValueError, KeyError, AttributeError) as e:
                print(f"EXIF解析错误 {photo_path}: {e}")
        
        # 3. 如果没有EXIF数据，使用文件修改时间
        return datetime.fromtimestamp(os.path.getmtime(photo_path))
        
    except Exception as e:
        print(f"处理图片失败 {photo_path}: {e}")
        return datetime.min
def scan_photos():
    """扫描桌面的照片文件"""
    desktop_path = Path.home() / "Desktop"
    
    # 支持的图片格式
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.tiff', '*.bmp', '*.gif']
    photo_files = []
    
    for ext in extensions:
        photo_files.extend(desktop_path.glob(ext))
        photo_files.extend(desktop_path.glob(ext.upper()))
    
    # 获取每张照片的拍摄时间和路径，并按时间排序
    photos_with_dates = []
    for photo_path in photo_files:
        creation_date = get_photo_creation_date(str(photo_path))
        photos_with_dates.append((creation_date, str(photo_path)))
    
    # 按拍摄时间从最近到最远排序
    photos_with_dates.sort(key=lambda x: x[0], reverse=True)
    
    return photos_with_dates

def display_photos_gui(photos_list):
    """创建GUI界面显示照片信息"""
    root = tk.Tk()
    root.title("桌面照片管理器 - 按拍摄时间排序")
    root.geometry("800x600")
    
    # 创建标题
    title_label = tk.Label(root, text="桌面照片列表 (按拍摄时间排序)", font=("Arial", 14))
    title_label.pack(pady=10)
    
    # 创建滚动文本框
    text_area = scrolledtext.ScrolledText(root, width=95, height=30)
    text_area.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
    
    # 插入照片信息
    for date, path in photos_list:
        formatted_date = date.strftime("%Y-%m-%d %H:%M:%S")
        text_area.insert(tk.END, f"[{formatted_date}] {path}\n")
    
    # 设置文本框为只读
    text_area.config(state=tk.DISABLED)
    
    # 运行GUI主循环
    root.mainloop()

def main():
    """主函数"""
    print("正在扫描桌面照片...")
    photos = scan_photos()
    
    if not photos:
        print("未找到任何照片文件！")
        input("按回车键退出...")
        return
    
    print(f"找到 {len(photos)} 张照片，正在启动界面...")
    display_photos_gui(photos)

if __name__ == "__main__":
    main()