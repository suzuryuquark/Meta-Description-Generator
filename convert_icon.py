from PIL import Image
import os

png_path = "seo_ai_icon.png"
ico_path = "icon.ico"

# Check if png exists in current dir, if not check artifacts dir
if not os.path.exists(png_path):
    # Try to find it in the artifacts directory if known, but for now we assume it's copied or we use the absolute path from generation
    # Since I can't easily get the absolute path from the previous tool output programmatically without parsing, 
    # I will assume I need to copy it first or use the path I know.
    # Actually, I'll just use the absolute path I saw in the output:
    # C:/Users/suzur/.gemini/antigravity/brain/270f1b5d-5629-4a71-9444-f8c1979a0b69/seo_ai_icon_1763886147838.png
    # But the filename has a timestamp. I should have used a fixed name or listed the dir.
    pass

# I'll handle the file copy in a separate step or use the list_dir to find it.
# For now, let's just write the converter function.

def convert_to_ico(source, target):
    img = Image.open(source)
    img.save(target, format='ICO', sizes=[(256, 256)])
    print(f"Converted {source} to {target}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        convert_to_ico(sys.argv[1], ico_path)
    else:
        print("Usage: python convert_icon.py <path_to_png>")
