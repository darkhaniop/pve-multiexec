import json


def to_list_validator(value: str | list) -> list:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    else:
        return json.loads(value)
