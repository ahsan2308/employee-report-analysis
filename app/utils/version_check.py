"""
Utility functions for checking package versions.
"""
from app.core.logger import logger

def check_qdrant_version():
    """
    Check if the installed qdrant-client meets the version requirements for group_by functionality.
    Minimum required version is 1.11.0.
    
    Returns:
        tuple: (meets_requirements, version_string)
    """
    try:
        import pkg_resources
        from packaging import version
        
        # Get the installed version
        qdrant_version = pkg_resources.get_distribution("qdrant-client").version
        
        # Parse version string to check if it meets requirements
        v = version.parse(qdrant_version)
        min_required = version.parse("1.11.0")
        
        logger.info(f"Installed qdrant-client version: {qdrant_version}")
        
        if v < min_required:
            logger.warning(f"Qdrant client version {qdrant_version} is below the minimum required version 1.11.0 for group_by functionality")
            return False, qdrant_version
        else:
            logger.info(f"Qdrant client version {qdrant_version} meets requirements (>= 1.11.0)")
            return True, qdrant_version
            
    except ImportError:
        logger.error("Could not import required packages to check version")
        return False, "unknown"
    except Exception as e:
        logger.error(f"Error checking qdrant-client version: {e}")
        return False, "unknown"

if __name__ == "__main__":
    """Run this file directly to check the Qdrant client version."""
    meets_requirements, version = check_qdrant_version()
    print(f"Qdrant client version: {version}")
    print(f"Meets requirements for group_by functionality: {meets_requirements}")
    
    if not meets_requirements:
        print("To upgrade: pip install --upgrade qdrant-client>=1.11.0")
