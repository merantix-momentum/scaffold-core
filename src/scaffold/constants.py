import os
from pathlib import Path

import scaffold

MODULE_PATH = os.path.dirname(scaffold.__file__)
MANIFEST_DIR = Path(os.path.join(MODULE_PATH, "manifests"))

ARTIFACT_META_DIR = "meta"
ARTIFACT_DESCRIPTION_FILE = "readme.txt"

RUNTIME_CFG_KEY: str = "runtime_cfg"
