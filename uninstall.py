import os
import shutil

def main():
    node_dir = os.path.dirname(os.path.abspath(__file__))
    wildcards_dir = os.path.join(node_dir, "wildcards")
    parent_dir = os.path.dirname(node_dir)  # the custom_nodes folder
    backup_dir = os.path.join(parent_dir, ".comfyui_local_wildcards_backup")

    if not os.path.isdir(wildcards_dir):
        print("[comfyui_local_wildcards] No wildcards folder found, nothing to back up.")
        return

    try:
        if os.path.isdir(backup_dir):
            shutil.rmtree(backup_dir)
        shutil.copytree(wildcards_dir, backup_dir)
        print(f"[comfyui_local_wildcards] Backed up wildcards folder to: {backup_dir}")
    except Exception as e:
        print(f"[comfyui_local_wildcards] WARNING: failed to back up wildcards folder: {e}")

if __name__ == "__main__":
    main()