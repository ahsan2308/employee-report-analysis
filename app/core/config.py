import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the absolute path to config.yaml
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Moves one level up from 'core'
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")

# Ensure the config file exists
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"Config file not found at: {CONFIG_PATH}")

# Load configurations from YAML file
with open(CONFIG_PATH, "r") as file:
    config = yaml.safe_load(file)

# Database Config (Constructing DATABASE_URL dynamically)
DB_USER = os.getenv("DB_USER", config["database"]["user"])
DB_PASSWORD = os.getenv("DB_PASSWORD", config["database"]["password"])
DB_HOST = os.getenv("DB_HOST", config["database"]["host"])
DB_PORT = os.getenv("DB_PORT", str(config["database"]["port"]))  # Ensure it's a string
DB_NAME = os.getenv("DB_NAME", config["database"]["name"])

DATABASE_URL = os.getenv(
    "DATABASE_URL", f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# LLM (Ollama) Config
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", config["llm"]["api_url"])
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", config["llm"]["model"])

# General App Config
DEBUG = os.getenv("DEBUG", str(config["app"]["debug"])).lower() in ("true", "1", "yes")

