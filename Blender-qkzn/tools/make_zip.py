"""打包脚本：将插件目录压缩成 zip 以供 Blender 安装。"""

from __future__ import annotations

import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDON_DIR = PROJECT_ROOT / "addons" / "blender_qkzn"
OUTPUT = PROJECT_ROOT / "blender_qkzn.zip"


def main() -> None:
    if not ADDON_DIR.exists():
        raise SystemExit(f"未找到插件目录: {ADDON_DIR}")

    print(f"正在打包 {ADDON_DIR} -> {OUTPUT}")
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in ADDON_DIR.rglob("*"):
            if path.is_file():
                arcname = path.relative_to(PROJECT_ROOT)
                zf.write(path, arcname.as_posix())
    print("打包完成")


if __name__ == "__main__":
    main()
