#!/usr/bin/env python3
import os
import shutil


def bundle_cas_jsons():
    """
    Scan the current directory for subfolders (one per annotated document),
    find the CAS JSON file inside each one, and copy it into a 'jsons'
    folder in the current directory.

    - No naming convention is required for the folders.
    - The output JSON will be named after the folder.

    Example:

      Current directory:
        article_001/
          CURATION_USER123.json
        some-other-doc/
          export.json
        jsons/                # (may or may not exist yet)
        bundle_cas_jsons.py

      After running:
        jsons/
          article_001.json
          some-other-doc.json
    """
    root_dir = os.getcwd()
    output_dir = os.path.join(root_dir, "jsons")
    os.makedirs(output_dir, exist_ok=True)

    entries = sorted(os.listdir(root_dir))
    for entry in entries:
        folder_path = os.path.join(root_dir, entry)

        # Skip non-directories and the output folder itself
        if not os.path.isdir(folder_path):
            continue
        if entry == "jsons":
            continue
        if entry.startswith("."):
            # skip hidden dirs like .git, .idea, etc.
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
            json_files.sort()
            print(f"[WARN] Multiple JSON files in {folder_path}, using first: {json_files[0]}")

        json_name = json_files[0]
        src_path = os.path.join(folder_path, json_name)

        # New name: use folder name (minus extension if any) + .json
        base_name, _ = os.path.splitext(entry)
        dest_name = base_name + ".json"
        dest_path = os.path.join(output_dir, dest_name)

        shutil.copy2(src_path, dest_path)
        print(f"[OK] {src_path} -> {dest_path}")

    print(f"[DONE] JSON files bundled into: {output_dir}")


if __name__ == "__main__":
    bundle_cas_jsons()
