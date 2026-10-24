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
        
    # Copy skin addon.xml and assets
    shutil.copy2(skin_addon_xml_path, os.path.join(skin_out_dir, "addon.xml"))
    for asset in ["icon.png", "fanart.jpg"]:
        src_asset = os.path.join(skin_source_dir, "resources", asset)
        if os.path.exists(src_asset):
            shutil.copy2(src_asset, os.path.join(skin_out_dir, asset))
            
    # Copy screenshots to web output for browser viewing and repository metadata
    src_screenshots = os.path.join(skin_source_dir, "resources", "screenshots")
    if os.path.exists(src_screenshots):
        dest_screenshots = os.path.join(skin_out_dir, "resources", "screenshots")
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
    
    # 7. Generate index.html for web and Kodi HTTP File Manager browsing
    # Kodi's HTTPDirectory parser requires a strict Apache-style directory listing format:
    # 1. 'href' must be the first attribute inside the <a> tag (no classes or other attributes before it).
    # 2. Each entry must be on a single line with trailing metadata (date, size) so the regex can match.
    # 3. The dot in Kodi's regex does not match newlines, so multiline HTML layouts fail.
    index_html_path = os.path.join(output_dir, "index.html")
    
    # Get current date/time in Apache format (e.g. 24-Jul-2026 21:49)
    import datetime
    now = datetime.datetime.now()
    apache_date = now.strftime("%d-%b-%Y %H:%M")
    
    index_html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Skynet Kodi Repository</title>
</head>
<body>
    <h1>Index of /</h1>
    <a href="../">Parent Directory</a>
    <a href="addons.xml">addons.xml</a>                                                                                                 {apache_date}      1.2K
    <a href="addons.xml.md5">addons.xml.md5</a>                                                                                           {apache_date}      32
    <a href="repository.skynet-1.0.0.zip">repository.skynet-1.0.0.zip</a>                                                                 {apache_date}      1.4M
    <a href="repository.skynet/">repository.skynet/</a>                                                                                   {apache_date}      -
    <a href="skin.skynet/">skin.skynet/</a>                                                                                               {apache_date}      -
</body>
</html>
"""
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write(index_html_content)
    print(f"[+] Generated {index_html_path}")
    print("[+] Repository build complete successfully!")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python build_kodi_repo.py <skin_source_dir> <repo_addon_dir> <output_dir>")
        sys.exit(1)
    build_repo(sys.argv[1], sys.argv[2], sys.argv[3])
