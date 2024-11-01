from models import BotConfig
import json
import msgspec

def get_config(filename: str):
    with open(filename, 'r') as cjson:
        config_body = json.load(cjson)
    config = msgspec.convert(config_body, BotConfig, strict=False)
    return config
