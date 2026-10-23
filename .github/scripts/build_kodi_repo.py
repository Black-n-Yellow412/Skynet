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
    index_html_path = os.path.join(output_dir, "index.html")
    index_html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skynet Kodi Repository</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            justify-content: center;
        }}
        .container {{
            max-width: 750px;
            width: 100%;
        }}
        h1 {{
            color: #f5c518;
            margin-bottom: 8px;
            font-size: 2rem;
        }}
        p.subtitle {{
            color: #8b949e;
            margin-top: 0;
            margin-bottom: 30px;
            font-size: 1.1rem;
        }}
        .card {{
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        h2 {{
            color: #ffffff;
            margin-top: 0;
            font-size: 1.3rem;
            border-bottom: 1px solid #30363d;
            padding-bottom: 10px;
        }}
        ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        li {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 16px;
            border-bottom: 1px solid #21262d;
        }}
        li:last-child {{
            border-bottom: none;
        }}
        a.download-btn {{
            background-color: #238636;
            color: #ffffff;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.95rem;
            display: inline-block;
        }}
        a.download-btn:hover {{
            background-color: #2ea043;
        }}
        .file-name {{
            font-family: monospace;
            font-size: 1rem;
            color: #58a6ff;
            text-decoration: none;
        }}
        .file-name:hover {{
            text-decoration: underline;
        }}
        .file-info {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .file-meta {{
            color: #8b949e;
            font-size: 0.85rem;
        }}
        ol {{
            padding-left: 20px;
            color: #c9d1d9;
            line-height: 1.6;
        }}
        code {{
            background-color: #21262d;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
            color: #79c0ff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Skynet Kodi Repository</h1>
        <p class="subtitle">Official auto-updating repository for Skynet Estuary Mod v2 (Kodi 22 Piers)</p>

        <div class="card">
            <h2>Add-on Downloads</h2>
            <ul>
                <li>
                    <div class="file-info">
                        <a class="file-name" href="{repo_zip_name}">{repo_zip_name}</a>
                        <span class="file-meta">Repository Installer (Install this in Kodi for auto-updates)</span>
                    </div>
                    <a class="download-btn" href="{repo_zip_name}">Download</a>
                </li>
                <li>
                    <div class="file-info">
                        <a class="file-name" href="{skin_id}/{skin_zip_name}">{skin_zip_name}</a>
                        <span class="file-meta">Skynet Skin v{skin_version} (Direct Zip)</span>
                    </div>
                    <a class="download-btn" href="{skin_id}/{skin_zip_name}">Download</a>
                </li>
            </ul>
        </div>

        <div class="card">
            <h2>How to Install in Kodi</h2>
            <ol>
                <li>In Kodi, navigate to <strong>Settings (Gear Icon) &gt; File manager &gt; Add source</strong>.</li>
                <li>Click <code>&lt;None&gt;</code> and enter this URL: <code>https://black-n-yellow412.github.io/Skynet/</code></li>
                <li>Name the source <strong>Skynet</strong> and click <strong>OK</strong>.</li>
                <li>Go back to the Home Screen &gt; <strong>Add-ons</strong> &gt; Box icon &gt; <strong>Install from zip file</strong>.</li>
                <li>Select <strong>Skynet</strong> and choose <code>{repo_zip_name}</code>.</li>
                <li>Once installed, select <strong>Install from repository</strong> &gt; <strong>Skynet Repository</strong> &gt; <strong>Look and feel</strong> &gt; <strong>Skin</strong> &gt; <strong>Skynet</strong>.</li>
            </ol>
        </div>
    </div>
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
