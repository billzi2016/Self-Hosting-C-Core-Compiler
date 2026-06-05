"""模块说明：让 `python -m c_core_compiler` 直接进入命令行入口。"""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
