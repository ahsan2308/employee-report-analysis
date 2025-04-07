import os
import yaml
from app.utils.env_loader import load_env_from_file

# Load environment variables from specific .env file
load_env_from_file()

# Get the absolute path of config.yaml
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../../config/config.yaml")

# Load configurations from YAML file
with open(CONFIG_PATH, "r") as file:
    config = yaml.safe_load(file)  # ✅ Reads config.yaml as a Python dictionary


# Test if config values are loading properly
print("Database URL:", config["database"]["url"])
print("LLM API URL:", config["llm"]["api_url"])
print("Debug Mode:", config["app"]["debug"])