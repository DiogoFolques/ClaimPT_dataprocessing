#!/usr/bin/env python3
import os
import shutil


def collect_jsons_from_news_dirs():
    """
    Scan the current directory for folders named like 'news_XXXX.txt',
    find the JSON file inside each one, and copy it into a 'jsons'
    folder in the current directory, renaming it to 'news_XXXX.json'.

    Example:
      Current directory:
        news_0001.txt/
          CURATION_USER5472656646486655855.json
        news_0002.txt/
          CURATION_USER1234567890123456789.json
        bundle_cas_jsons.py

      After running:
        jsons/
          news_0001.json
          news_0002.json
    """
    root_dir = os.getcwd()
    output_dir = os.path.join(root_dir, "jsons")
    os.makedirs(output_dir, exist_ok=True)

    entries = sorted(os.listdir(root_dir))
    for entry in entries:
        folder_path = os.path.join(root_dir, entry)

        # Only care about directories like "news_0001.txt"
        if not os.path.isdir(folder_path):
            continue
        if not entry.startswith("news_") or not entry.endswith(".txt"):
            continue

        # Find JSON files inside this folder
        json_files = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(".json")
        ]

        if len(json_files) == 0:
            print(f"[WARN] No JSON file found in {folder_path}, skipping.")
            continue
        elif len(json_files) > 1:
            print(f"[WARN] Multiple JSON files in {folder_path}, using first: {json_files[0]}")

        json_name = json_files[0]
        src_path = os.path.join(folder_path, json_name)

        # New name: same as folder, but .json (drop the .txt)
        base_name, _ = os.path.splitext(entry)   # 'news_0001.txt' -> ('news_0001', '.txt')
        dest_name = base_name + ".json"          # -> 'news_0001.json'
        dest_path = os.path.join(output_dir, dest_name)

        shutil.copy2(src_path, dest_path)
        print(f"[OK] {src_path} -> {dest_path}")

    print(f"[DONE] JSON files bundled into: {output_dir}")


if __name__ == "__main__":
    collect_jsons_from_news_dirs()
