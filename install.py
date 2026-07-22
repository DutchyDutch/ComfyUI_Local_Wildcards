import os
import shutil

def main():
    node_dir = os.path.dirname(os.path.abspath(__file__))
    wildcards_dir = os.path.join(node_dir, "wildcards")
    parent_dir = os.path.dirname(node_dir)
    backup_dir = os.path.join(parent_dir, ".comfyui_local_wildcards_backup")

    if not os.path.isdir(backup_dir):
        return  # nothing to restore, fresh install with no prior backup

    try:
        os.makedirs(wildcards_dir, exist_ok=True)
        for name in os.listdir(backup_dir):
            src = os.path.join(backup_dir, name)
            dst = os.path.join(wildcards_dir, name)
            if not os.path.exists(dst):
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        print(f"[comfyui_local_wildcards] Restored user wildcards from backup: {backup_dir}")
        shutil.rmtree(backup_dir)
    except Exception as e:
        print(f"[comfyui_local_wildcards] WARNING: failed to restore wildcards backup: {e}")

if __name__ == "__main__":
    main()