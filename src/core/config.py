from pathlib import Path
import yaml
from pydantic import BaseModel
from typing import Optional

class AppConfig(BaseModel):
    name: str
    version: str
    log_level: str = "INFO"

class LLMRoutingConfig(BaseModel):
    enabled: bool = True
    simple_threshold: int = 3
    complex_threshold: int = 7
    medium_preference: str = "local"

class Config(BaseModel):
    app: AppConfig
    llm_routing: LLMRoutingConfig

def load_config(config_path: str = "config/config.yaml") -> Config:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    return Config(**config_data)
