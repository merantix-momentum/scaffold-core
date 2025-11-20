from typing import Any, Dict, Optional

from pydantic import BaseModel


class MetaData(BaseModel):
    metadata: Optional[Dict[str, Any]] = {}
