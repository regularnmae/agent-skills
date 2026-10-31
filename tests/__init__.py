"""Test support: put `lib/` on the path so its modules import by bare name."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
