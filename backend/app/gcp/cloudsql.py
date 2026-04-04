from googleapiclient import discovery
from config.settings import settings
from src.lib.logger import setup_logger

logger = setup_logger("gcp.cloudsql")

def _get_service():
    """Get Cloud SQL Admin API service."""
    return discovery.build('sqladmin', 'v1', cache_discovery=False)

def list_instances(project_id: str = None):
    """Lists all Cloud SQL instances in the project with detailed info."""
    try:
        project = project_id or settings.project_id
        service = _get_service()
        
        request = service.instances().list(project=project)
        response = request.execute()
        
        instances = response.get('items', [])
        detailed_report = []

        for i in instances:
            settings_data = i.get('settings', {})
            
            detailed_report.append({
                "name": i.get('name'),
                "database_version": i.get('databaseVersion'),
                "state": i.get('state'),
                "location": i.get('region'),
                "edition": settings_data.get('edition', 'ENTERPRISE'),
                "tier": settings_data.get('tier'),
                "storage_details": {
                    "storage_type": settings_data.get('dataDiskType'),
                    "allocated_gb": settings_data.get('dataDiskSizeGb'),
                    "auto_resize": settings_data.get('storageAutoResize', True)
                },
                "labels": settings_data.get('userLabels', {}),
                "connection_name": i.get('connectionName'),
                "ipv4_address": next((ip.get('ipAddress') for ip in i.get('ipAddresses', []) if ip.get('type') == 'PRIMARY'), None)
            })
            
        logger.info(f"Listed {len(detailed_report)} Cloud SQL instances in project {project}.")
        return detailed_report
    except Exception as e:
        logger.error(f"Error listing Cloud SQL instances: {e}")
        return {"error": f"Failed to extract Cloud SQL data: {str(e)}"}

def get_instance_details(instance_name: str, project_id: str = None):
    """Gets detailed information for a specific Cloud SQL instance."""
    try:
        project = project_id or settings.project_id
        service = _get_service()
        
        i = service.instances().get(project=project, instance=instance_name).execute()
        settings_data = i.get('settings', {})
        
        details = {
            "name": i.get('name'),
            "database_version": i.get('databaseVersion'),
            "state": i.get('state'),
            "location": i.get('region'),
            "gce_zone": i.get('gceZone'),
            "edition": settings_data.get('edition', 'ENTERPRISE'),
            "tier": settings_data.get('tier'),
            "storage_details": {
                "storage_type": settings_data.get('dataDiskType'),
                "allocated_gb": settings_data.get('dataDiskSizeGb'),
                "auto_resize": settings_data.get('storageAutoResize', True)
            },
            "backup_enabled": settings_data.get('backupConfiguration', {}).get('enabled', False),
            "availability_type": settings_data.get('availabilityType', 'N/A'),
            "labels": settings_data.get('userLabels', {}),
            "connection_name": i.get('connectionName'),
            "ip_addresses": [{"ip": ip.get('ipAddress'), "type": ip.get('type')} for ip in i.get('ipAddresses', [])],
            "creation_time": i.get('createTime', 'N/A')
        }
        
        logger.info(f"Retrieved details for Cloud SQL instance: {instance_name}")
        return details
    except Exception as e:
        logger.error(f"Error getting Cloud SQL instance details for {instance_name}: {e}")
        return {"error": str(e)}

def list_databases(instance_name: str, project_id: str = None):
    """Lists all databases in a Cloud SQL instance."""
    try:
        project = project_id or settings.project_id
        service = _get_service()
        
        response = service.databases().list(project=project, instance=instance_name).execute()
        
        databases = []
        for db in response.get('items', []):
            databases.append({
                "name": db.get('name'),
                "charset": db.get('charset'),
                "collation": db.get('collation')
            })
            
        logger.info(f"Listed {len(databases)} databases in instance {instance_name}.")
        return databases
    except Exception as e:
        logger.error(f"Error listing databases: {e}")
        return {"error": str(e)}
