#!/usr/bin/env python3
"""
build_kodi_repo.py
Automates packaging Kodi addons and creating an auto-updating repository.
Outputs:
  - addons.xml & addons.xml.md5
  - repository.skynet/<zip>, .md5, addon.xml, icon.png
  - skin.skynet/<zip>, .md5, addon.xml, icon.png
  - repository.skynet-1.0.0.zip (root level for 1-click Kodi File Manager download)
  - index.html (web directory listing for Kodi File Manager)
"""

import os
import sys
import shutil
import hashlib
import zipfile
import xml.etree.ElementTree as ET

def get_md5(filepath):
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def create_addon_zip(source_dir, output_zip_path, addon_id, exclude_patterns=None, is_skin=False):
    if exclude_patterns is None:
        exclude_patterns = {
            ".git", ".github", "__pycache__", ".gitignore", ".DS_Store",
            "build", "dist", "Working_Backups", "AI Workshop", "UI_Research"
        }
    
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in exclude_patterns and not d.startswith(".")]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_dir)
                norm_rel = rel_path.replace("\\", "/")
                # For skin installable zip, exclude screenshots (documentation only, not used by Kodi runtime)
                # This keeps the zip safely under GitHub's 100 MB hard limit.
                if is_skin and norm_rel.startswith("resources/screenshots"):
                    continue
                if file in exclude_patterns or file.endswith(".pyc") or file.endswith(".zip") or file.endswith(".md5"):
                    continue
                arcname = os.path.join(addon_id, rel_path)
                zf.write(full_path, arcname)

def generate_apache_index(dir_path, title, is_root=False):
    import datetime
    now = datetime.datetime.now()
    apache_date = now.strftime("%d-%b-%Y %H:%M")
    
    entries = []
    if not is_root:
        entries.append(f'<a href="../">Parent Directory</a>{" " * 50}-')
        
    items = sorted(os.listdir(dir_path))
    dirs = [i for i in items if os.path.isdir(os.path.join(dir_path, i)) and not i.startswith(".")]
    files = [i for i in items if os.path.isfile(os.path.join(dir_path, i)) and not i.startswith(".") and i != "index.html"]
    
    for d in dirs:
        d_name = f"{d}/"
        spacing = max(1, 58 - len(d_name))
        entries.append(f'<a href="{d_name}">{d_name}</a>{" " * spacing}{apache_date}{" " * 12}-')
        
    for f in files:
        f_path = os.path.join(dir_path, f)
        f_size = os.path.getsize(f_path)
        spacing = max(1, 58 - len(f))
        size_str = str(f_size)
        size_spacing = max(1, 14 - len(size_str))
        entries.append(f'<a href="{f}">{f}</a>{" " * spacing}{apache_date}{" " * size_spacing}{size_str}')
        
    content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{title}</title></head>
<body>
<h1>{title}</h1>
<pre>
""" + "\n".join(entries) + """
</pre>
</body>
</html>
"""
    with open(os.path.join(dir_path, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

def build_repo(skin_source_dir, repo_addon_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Parse Skin addon.xml
    skin_addon_xml_path = os.path.join(skin_source_dir, "addon.xml")
    if not os.path.exists(skin_addon_xml_path):
        raise FileNotFoundError(f"Missing addon.xml in {skin_source_dir}")
    
    skin_tree = ET.parse(skin_addon_xml_path)
    skin_root = skin_tree.getroot()
    skin_id = skin_root.get("id", "skin.skynet")
    skin_version = skin_root.get("version", "22.0+piers")
    
    print(f"[+] Skin Addon: {skin_id} v{skin_version}")
    
    # 2. Parse Repository addon.xml
    repo_addon_xml_path = os.path.join(repo_addon_dir, "addon.xml")
    if not os.path.exists(repo_addon_xml_path):
        raise FileNotFoundError(f"Missing addon.xml in {repo_addon_dir}")
        
    repo_tree = ET.parse(repo_addon_xml_path)
    repo_root = repo_tree.getroot()
    repo_id = repo_root.get("id", "repository.skynet")
    repo_version = repo_root.get("version", "1.0.0")
    
    print(f"[+] Repo Addon: {repo_id} v{repo_version}")
    
    # 3. Create output directory structure
    skin_out_dir = os.path.join(output_dir, skin_id)
    repo_out_dir = os.path.join(output_dir, repo_id)
    os.makedirs(skin_out_dir, exist_ok=True)
    os.makedirs(repo_out_dir, exist_ok=True)
    
    # 4. Package Skin Zip
    skin_zip_name = f"{skin_id}-{skin_version}.zip"
    skin_zip_path = os.path.join(skin_out_dir, skin_zip_name)
    print(f"[+] Packaging skin into {skin_zip_path}...")
    create_addon_zip(skin_source_dir, skin_zip_path, skin_id, is_skin=True)
    
    # Generate Skin Zip MD5
    skin_zip_md5 = get_md5(skin_zip_path)
    with open(f"{skin_zip_path}.md5", "w", encoding="utf-8") as f:
        f.write(skin_zip_md5)
        
    # Copy skin addon.xml and assets (both root and resources/ subfolder for Kodi compatibility)
    shutil.copy2(skin_addon_xml_path, os.path.join(skin_out_dir, "addon.xml"))
    skin_resources_dir = os.path.join(skin_out_dir, "resources")
    os.makedirs(skin_resources_dir, exist_ok=True)
    for asset in ["icon.png", "fanart.jpg"]:
        src_asset = os.path.join(skin_source_dir, "resources", asset)
        if os.path.exists(src_asset):
            shutil.copy2(src_asset, os.path.join(skin_out_dir, asset))
            shutil.copy2(src_asset, os.path.join(skin_resources_dir, asset))
            
    # Copy screenshots to web output for browser viewing and repository metadata
    src_screenshots = os.path.join(skin_source_dir, "resources", "screenshots")
    dest_screenshots = os.path.join(skin_resources_dir, "screenshots")
    if os.path.exists(src_screenshots):
        os.makedirs(dest_screenshots, exist_ok=True)
        for s in os.listdir(src_screenshots):
            shutil.copy2(os.path.join(src_screenshots, s), os.path.join(dest_screenshots, s))
            
    # 5. Package Repo Zip
    repo_zip_name = f"{repo_id}-{repo_version}.zip"
    repo_zip_path = os.path.join(repo_out_dir, repo_zip_name)
    print(f"[+] Packaging repository into {repo_zip_path}...")
    create_addon_zip(repo_addon_dir, repo_zip_path, repo_id)
    
    # Generate Repo Zip MD5
    repo_zip_md5 = get_md5(repo_zip_path)
    with open(f"{repo_zip_path}.md5", "w", encoding="utf-8") as f:
        f.write(repo_zip_md5)
        
    # Copy repo addon.xml and assets
    shutil.copy2(repo_addon_xml_path, os.path.join(repo_out_dir, "addon.xml"))
    for asset in ["icon.png", "fanart.jpg"]:
        src_asset = os.path.join(repo_addon_dir, asset)
        if os.path.exists(src_asset):
            shutil.copy2(src_asset, os.path.join(repo_out_dir, asset))
            
    # Copy repo zip to root output directory as well for 1-click Kodi File Manager download
    shutil.copy2(repo_zip_path, os.path.join(output_dir, repo_zip_name))
    
    # 6. Generate master addons.xml
    addons_root = ET.Element("addons")
    addons_root.append(repo_root)
    addons_root.append(skin_root)
    
    master_addons_xml_path = os.path.join(output_dir, "addons.xml")
    tree = ET.ElementTree(addons_root)
    ET.indent(tree, space="  ", level=0)
    tree.write(master_addons_xml_path, encoding="utf-8", xml_declaration=True)
    print(f"[+] Generated {master_addons_xml_path}")
    
    # Generate master addons.xml.md5
    master_md5 = get_md5(master_addons_xml_path)
    master_md5_path = os.path.join(output_dir, "addons.xml.md5")
    with open(master_md5_path, "w", encoding="utf-8") as f:
        f.write(master_md5)
    print(f"[+] Generated {master_md5_path}")
    
    # 7. Generate Apache-compatible index.html directory listings
    # Kodi's HTTPDirectory parser requires:
    # 1. 'href' must be the first attribute inside the <a> tag.
    # 2. Each entry must be on a single line with trailing metadata (date, integer byte size).
    # 3. Sizes must be exact integers in bytes (no decimals like 1.4M) so Kodi's reSize regex captures the exact byte length.
    generate_apache_index(output_dir, "Index of /", is_root=True)
    generate_apache_index(repo_out_dir, f"Index of /{repo_id}/", is_root=False)
    generate_apache_index(skin_out_dir, f"Index of /{skin_id}/", is_root=False)
    if os.path.exists(skin_resources_dir):
        generate_apache_index(skin_resources_dir, f"Index of /{skin_id}/resources/", is_root=False)
    if os.path.exists(dest_screenshots):
        generate_apache_index(dest_screenshots, f"Index of /{skin_id}/resources/screenshots/", is_root=False)
    print(f"[+] Generated Apache directory indexes in all repository folders")
    print("[+] Repository build complete successfully!")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python build_kodi_repo.py <skin_source_dir> <repo_addon_dir> <output_dir>")
        sys.exit(1)
    build_repo(sys.argv[1], sys.argv[2], sys.argv[3])
