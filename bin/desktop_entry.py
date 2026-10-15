"""PyInstaller desktop entry; CLI remains a separate console executable."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gpt_usage.cli import main
raise SystemExit(main([*sys.argv[1:], "desktop"]))
