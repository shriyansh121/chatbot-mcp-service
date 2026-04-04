from google.cloud import functions_v2
from app.lib.config import settings
from app.lib.logger import setup_logger

logger = setup_logger("gcp.functions")

def list_functions(project_id: str = None):
    """Lists all Cloud Functions (v2/Gen2) in the project."""
    try:
        project = project_id or settings.project_id
        client = functions_v2.FunctionServiceClient()
        location_parent = f"projects/{project}/locations/-"
        
        functions = client.list_functions(parent=location_parent)
        
        result = []
        for fn in functions:
            result.append({
                "name": fn.name.split('/')[-1],
                "state": fn.state.name,
                "environment": fn.environment.name,
                "entry_point": fn.build_config.entry_point if fn.build_config else "N/A",
                "runtime": fn.build_config.runtime if fn.build_config else "N/A",
                "update_time": str(fn.update_time)
            })
            
        logger.info(f"Listed {len(result)} Cloud Functions in project {project}.")
        return result
    except Exception as e:
        logger.error(f"Error fetching Cloud Functions: {e}")
        return []

def get_function_details(function_name: str, project_id: str = None):
    """Gets detailed information for a specific Cloud Function."""
    try:
        project = project_id or settings.project_id
        client = functions_v2.FunctionServiceClient()
        location_parent = f"projects/{project}/locations/-"
        
        functions = client.list_functions(parent=location_parent)
        
        for fn in functions:
            if fn.name.split('/')[-1] == function_name:
                details = {
                    "name": fn.name.split('/')[-1],
                    "full_name": fn.name,
                    "state": fn.state.name,
                    "environment": fn.environment.name,
                    "entry_point": fn.build_config.entry_point if fn.build_config else "N/A",
                    "runtime": fn.build_config.runtime if fn.build_config else "N/A",
                    "url": fn.url if hasattr(fn, 'url') and fn.url else "N/A",
                    "update_time": str(fn.update_time),
                    "service_config": {
                        "service_account_email": fn.service_config.service_account_email if fn.service_config else "N/A",
                        "available_memory": fn.service_config.available_memory if fn.service_config else "N/A",
                        "timeout_seconds": fn.service_config.timeout_seconds if fn.service_config else "N/A"
                    } if fn.service_config else {}
                }
                logger.info(f"Retrieved details for function: {function_name}")
                return details
        
        return {"error": f"Function {function_name} not found"}
    except Exception as e:
        logger.error(f"Error getting function details for {function_name}: {e}")
        return {"error": str(e)}
