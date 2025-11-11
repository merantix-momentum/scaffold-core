from __future__ import annotations

from typing import Any, Dict, List, Optional

from docarray import BaseDoc
from pydantic import BaseModel, create_model, Field

from scaffold.data.catalog.dataloader import DATALOADER

BASIC_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
}


def create_pydantic_model_from_json_schema(schema):
    """
    Creates a Pydantic model from a JSON schema.
    Inspired by: https://gist.github.com/h55nick/0e1d48b72ab9c5db33b89ba0443f41e7
    """
    klass = schema.get("title", "Model")
    fields = {}
    for prop_name, prop_info in schema["properties"].items():
        field_type = prop_info.get("type", "default")
        py_type = None
        if field_type == "default" or prop_name in ["properties", "required", "default", "additionalProperties"]:
            continue
        if field_type == "array":
            item_type = prop_info["items"]["type"]
            if item_type == "object":
                py_type = list[create_pydantic_model_from_json_schema(f"{klass}_{prop_name}", prop_info["items"])]
            else:
                py_type = list[BASIC_TYPE_MAP.get(item_type, None)]
        elif field_type == "object":
            if prop_info.get("properties", None):
                py_type = create_pydantic_model_from_json_schema(f"{klass}_{prop_name}", prop_info)
            elif prop_info.get("$ref"):
                ref_info = schema["properties"].get(prop_info["$ref"].split("/")[-1])
                py_type = create_pydantic_model_from_json_schema(f"{klass}_{prop_name}", ref_info)
            elif prop_info.get("additionalProperties", {}).get("$ref", None):
                ref_info = schema["properties"].get(prop_info["additionalProperties"]["$ref"].split("/")[-1])
                py_type = dict[str, create_pydantic_model_from_json_schema(f"{klass}_{prop_name}", ref_info)]
            else:
                raise Exception(f"Object Error, {py_type} {prop_name} for {field_type}")
        elif BASIC_TYPE_MAP.get(field_type):
            py_type = BASIC_TYPE_MAP[field_type]

        if py_type is None:
            raise Exception(f"Error, {py_type} for {field_type}")

        default = prop_info.get("default", ...) if prop_name in schema.get("required", []) else ...
        description = prop_info.get("description", "")
        fields[prop_name] = (py_type, Field(default, description=description))

    return create_model(klass, **fields, __base__=BaseDoc)


class DataSource(BaseModel):
    loader_id: str
    args: List = []
    kwargs: Dict = {}

    def load(self, **kwargs) -> Any:
        ret = DATALOADER[self.loader_id](*self.args, **(self.kwargs | kwargs))
        return ret

    def builder(loader_id: str, *args, **kwargs) -> DataSource:
        return DataSource(loader_id=loader_id, args=args, kwargs=kwargs)


class DataProduct(BaseModel):
    source: DataSource
    entity: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, str]] = None
