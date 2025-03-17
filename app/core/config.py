import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load configurations from YAML file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../../config/config.yaml")

with open(CONFIG_PATH, "r") as file:
    config = yaml.safe_load(file)

# Database Config
DATABASE_URL = os.getenv("DATABASE_URL", config["database"]["url"])

# LLM (Ollama) Config
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", config["llm"]["api_url"])
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", config["llm"]["model"])

# General App Config
DEBUG = os.getenv("DEBUG", config["app"]["debug"])
