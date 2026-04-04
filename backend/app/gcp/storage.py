from google.cloud import storage as gcs
from app.lib_helper.config import settings
from app.lib_helper.logger import setup_logger

logger = setup_logger("gcp.storage")

def list_buckets(project_id: str = None):
    """Lists all Cloud Storage buckets."""
    try:
        project = project_id or settings.project_id
        client = gcs.Client(project=project)
        buckets = client.list_buckets()
        
        bucket_list = []
        for bucket in buckets:
            bucket_list.append({
                "name": bucket.name,
                "location": bucket.location,
                "storage_class": bucket.storage_class,
                "created": str(bucket.time_created)
            })
            
        logger.info(f"Listed {len(bucket_list)} buckets in project {project}.")
        return bucket_list
    except Exception as e:
        logger.error(f"Error listing buckets: {e}")
        return []

def get_bucket_details(bucket_name: str):
    """Gets detailed information for a specific bucket."""
    try:
        client = gcs.Client()
        bucket = client.get_bucket(bucket_name)
        
        details = {
            "name": bucket.name,
            "id": bucket.id,
            "location": bucket.location,
            "location_type": bucket.location_type,
            "storage_class": bucket.storage_class,
            "created": str(bucket.time_created),
            "updated": str(bucket.updated),
            "versioning_enabled": bucket.versioning_enabled,
            "labels": dict(bucket.labels) if bucket.labels else {},
            "lifecycle_rules": [str(rule) for rule in bucket.lifecycle_rules] if bucket.lifecycle_rules else [],
            "cors": bucket.cors,
            "default_event_based_hold": bucket.default_event_based_hold,
            "requester_pays": bucket.requester_pays
        }
        
        logger.info(f"Retrieved details for bucket: {bucket_name}")
        return details
    except Exception as e:
        logger.error(f"Error getting bucket details for {bucket_name}: {e}")
        return {"error": str(e)}
