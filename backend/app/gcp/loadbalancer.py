from google.cloud import compute_v1
from app.lib.config import settings
from app.lib.logger import setup_logger

logger = setup_logger("gcp.loadbalancer")

def list_url_maps(project_id: str = None):
    """Lists all URL Maps (HTTP(S) Load Balancers) in the project."""
    try:
        project = project_id or settings.project_id
        client = compute_v1.UrlMapsClient()
        
        request = compute_v1.ListUrlMapsRequest(project=project)
        response = client.list(request=request)
        
        url_maps = []
        for url_map in response:
            url_maps.append({
                "name": url_map.name,
                "default_service": url_map.default_service.split("/")[-1] if url_map.default_service else "N/A",
                "creation_timestamp": url_map.creation_timestamp
            })
            
        logger.info(f"Listed {len(url_maps)} URL Maps in project {project}.")
        return url_maps
    except Exception as e:
        logger.error(f"Error listing URL Maps: {e}")
        return []

def list_forwarding_rules(project_id: str = None):
    """Lists all global forwarding rules (frontend of load balancers)."""
    try:
        project = project_id or settings.project_id
        client = compute_v1.GlobalForwardingRulesClient()
        
        request = compute_v1.ListGlobalForwardingRulesRequest(project=project)
        response = client.list(request=request)
        
        rules = []
        for rule in response:
            rules.append({
                "name": rule.name,
                "ip_address": rule.I_p_address,
                "port_range": rule.port_range,
                "target": rule.target.split("/")[-1] if rule.target else "N/A",
                "ip_protocol": rule.I_p_protocol,
                "load_balancing_scheme": rule.load_balancing_scheme,
                "creation_timestamp": rule.creation_timestamp
            })
            
        logger.info(f"Listed {len(rules)} global forwarding rules in project {project}.")
        return rules
    except Exception as e:
        logger.error(f"Error listing forwarding rules: {e}")
        return []

def list_backend_services(project_id: str = None):
    """Lists all backend services in the project."""
    try:
        project = project_id or settings.project_id
        client = compute_v1.BackendServicesClient()
        
        request = compute_v1.ListBackendServicesRequest(project=project)
        response = client.list(request=request)
        
        services = []
        for svc in response:
            services.append({
                "name": svc.name,
                "protocol": svc.protocol,
                "port": svc.port,
                "timeout_sec": svc.timeout_sec,
                "health_checks": [hc.split("/")[-1] for hc in svc.health_checks] if svc.health_checks else [],
                "backends_count": len(svc.backends) if svc.backends else 0,
                "creation_timestamp": svc.creation_timestamp
            })
            
        logger.info(f"Listed {len(services)} backend services in project {project}.")
        return services
    except Exception as e:
        logger.error(f"Error listing backend services: {e}")
        return []

def list_load_balancers(project_id: str = None):
    """Lists all load balancers (aggregated view of URL Maps + Forwarding Rules)."""
    try:
        project = project_id or settings.project_id
        
        url_maps = list_url_maps(project_id=project)
        forwarding_rules = list_forwarding_rules(project_id=project)
        backend_services = list_backend_services(project_id=project)
        
        return {
            "url_maps": url_maps,
            "forwarding_rules": forwarding_rules,
            "backend_services": backend_services,
            "summary": {
                "total_url_maps": len(url_maps),
                "total_forwarding_rules": len(forwarding_rules),
                "total_backend_services": len(backend_services)
            }
        }
    except Exception as e:
        logger.error(f"Error listing load balancers: {e}")
        return {"error": str(e)}
