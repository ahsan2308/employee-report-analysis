import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the absolute path of config.yaml
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../../config/config.yaml")

# Load configurations from YAML file
with open(CONFIG_PATH, "r") as file:
    config = yaml.safe_load(file)  # ✅ Reads config.yaml as a Python dictionary


# Test if config values are loading properly
print("Database URL:", config["database"]["url"])
print("LLM API URL:", config["llm"]["api_url"])
print("Debug Mode:", config["app"]["debug"])