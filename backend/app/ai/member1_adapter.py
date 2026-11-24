import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PREDICTOR_PATH = PROJECT_ROOT / "predictor.py"
MODULE_NAME = "floraguard_root_predictor"
spec = importlib.util.spec_from_file_location(MODULE_NAME, PREDICTOR_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load Member 1 predictor from {PREDICTOR_PATH}")

root_module = importlib.util.module_from_spec(spec)
root_path = str(PROJECT_ROOT)
added_root_to_path = root_path not in sys.path
if added_root_to_path:
    sys.path.insert(0, root_path)
try:
    spec.loader.exec_module(root_module)
finally:
    if added_root_to_path:
        sys.path.remove(root_path)

predict_image = root_module.predict_image
