from google.cloud import dns
from app.lib.config import settings
from app.lib.logger import setup_logger

logger = setup_logger("gcp.dns")

def list_zones(project_id: str = None):
    """Lists all DNS zones in the project."""
    try:
        project = project_id or settings.project_id
        client = dns.Client(project=project)
        
        zones = client.list_zones()
        
        zone_list = []
        for zone in zones:
            zone_list.append({
                "name": zone.name,
                "dns_name": zone.dns_name,
                "description": zone.description,
                "visibility": zone.visibility if hasattr(zone, 'visibility') else "public",
                "created": str(zone.created) if hasattr(zone, 'created') else "N/A"
            })
            
        logger.info(f"Listed {len(zone_list)} DNS zones in project {project}.")
        return zone_list
    except Exception as e:
        logger.error(f"Error listing DNS zones: {e}")
        return []

def get_zone_details(zone_name: str, project_id: str = None):
    """Gets detailed information for a specific DNS zone."""
    try:
        project = project_id or settings.project_id
        client = dns.Client(project=project)
        
        zone = client.zone(zone_name)
        zone.reload()
        
        # Get record sets
        records = []
        for record_set in zone.list_resource_record_sets():
            records.append({
                "name": record_set.name,
                "type": record_set.record_type,
                "ttl": record_set.ttl,
                "rrdatas": record_set.rrdatas
            })
        
        details = {
            "name": zone.name,
            "dns_name": zone.dns_name,
            "description": zone.description,
            "name_servers": zone.name_servers if hasattr(zone, 'name_servers') else [],
            "visibility": zone.visibility if hasattr(zone, 'visibility') else "public",
            "record_sets_count": len(records),
            "record_sets": records[:20]  # Limit to first 20 records
        }
        
        logger.info(f"Retrieved details for DNS zone: {zone_name}")
        return details
    except Exception as e:
        logger.error(f"Error getting DNS zone details for {zone_name}: {e}")
        return {"error": str(e)}

def list_record_sets(zone_name: str, project_id: str = None):
    """Lists all record sets in a DNS zone."""
    try:
        project = project_id or settings.project_id
        client = dns.Client(project=project)
        
        zone = client.zone(zone_name)
        
        records = []
        for record_set in zone.list_resource_record_sets():
            records.append({
                "name": record_set.name,
                "type": record_set.record_type,
                "ttl": record_set.ttl,
                "rrdatas": record_set.rrdatas
            })
            
        logger.info(f"Listed {len(records)} record sets in zone {zone_name}.")
        return records
    except Exception as e:
        logger.error(f"Error listing record sets: {e}")
        return []
