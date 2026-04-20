import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_PATHS = [
    ROOT / "apps" / "api" / "src",
    ROOT / "apps" / "producer" / "src",
    ROOT / "apps" / "stream-worker" / "src",
    ROOT / "apps" / "trainer" / "src",
    ROOT / "libs" / "common" / "src",
    ROOT / "libs" / "contracts" / "src",
    ROOT / "libs" / "feature_engineering" / "src",
    ROOT / "libs" / "feature_store" / "src",
    ROOT / "libs" / "model_runtime" / "src",
    ROOT / "libs" / "observability" / "src",
    ROOT / "libs" / "persistence" / "src",
    ROOT / "libs" / "rules" / "src",
]

for path in SRC_PATHS:
    sys.path.insert(0, str(path))
