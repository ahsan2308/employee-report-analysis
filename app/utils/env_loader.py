import os
from dotenv import load_dotenv
from functools import lru_cache

@lru_cache()
def load_env_from_file():
    """
    Load environment variables from a specific .env file.
    This function uses lru_cache to ensure it only loads the environment once.
    """
    # Get the absolute path to the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    
    # Get the path to the .env file
    env_path = os.path.join(project_root, ".env")
    
    # Load environment variables from the specified file
    # Add override=True to ensure project .env variables take precedence over any existing ones
    load_dotenv(dotenv_path=env_path, override=True)
    
    return True
