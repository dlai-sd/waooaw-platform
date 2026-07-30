import sys
from pathlib import Path

# billing-engine uses flat imports (WORKDIR=/app in Docker)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))
