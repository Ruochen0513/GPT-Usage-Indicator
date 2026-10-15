#!/usr/bin/env python3
"""Run the source checkout without installation, from any working directory."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gpt_usage.cli import main
raise SystemExit(main())
