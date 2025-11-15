import json
import logging
from google.cloud import storage

# Configure logging
logger = logging.getLogger(__name__)

# Configure Google Cloud Storage
storage_client = storage.Client()
bucket_name = "recreational-deployment.appspot.com"
bucket = storage_client.bucket(bucket_name)

def load_json_file_from_gcs(blob_name):
    try:
        blob = bucket.blob(blob_name)
        data = json.loads(blob.download_as_string())
        logger.info(f"Data loaded successfully from GCS: {blob_name}")
        return data
    except Exception as e:
        logger.error(f"Error loading JSON from GCS: {blob_name}: {e}")
        raise

def save_json_file_to_gcs(blob_name, data):
    try:
        blob = bucket.blob(blob_name)
        blob.upload_from_string(json.dumps(data, indent=4))
        logger.info(f"Data saved successfully to GCS: {blob_name}")
    except Exception as e:
        logger.error(f"Error saving JSON to GCS: {blob_name}: {e}")
        raise
