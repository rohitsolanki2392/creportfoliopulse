import os
from google.cloud import secretmanager
import logging

logger = logging.getLogger(__name__)

def get_secret(secret_id: str) -> str:
    """Fetches a secret from Google Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(name=name)
        secret_value = response.payload.data.decode("UTF-8")
        logger.info(f"Successfully fetched secret: {secret_id}")
        return secret_value
    except Exception as e:
        logger.error(f"Failed to fetch secret {secret_id}: {str(e)}")
        raise