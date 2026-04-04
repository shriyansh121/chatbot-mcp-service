from google.cloud import container_v1
from config.settings import settings
from src.lib.logger import setup_logger

logger = setup_logger("gcp.gke")

def list_clusters(project_id: str = None):
    """Lists all GKE clusters in the project."""
    try:
        project = project_id or settings.project_id
        client = container_v1.ClusterManagerClient()
        # Use "-" to list clusters across all locations
        parent = f"projects/{project}/locations/-"
        
        response = client.list_clusters(parent=parent)
        
        clusters = []
        for cluster in response.clusters:
            clusters.append({
                "name": cluster.name,
                "status": str(cluster.status),
                "location": cluster.location,
                "node_count": cluster.current_node_count,
                "master_version": cluster.current_master_version,
                "endpoint": cluster.endpoint
            })
            
        logger.info(f"Listed {len(clusters)} GKE clusters in project {project}.")
        return clusters
    except Exception as e:
        logger.error(f"Error listing GKE clusters: {e}")
        return []

def get_cluster_details(cluster_name: str, project_id: str = None):
    """Gets detailed information for a specific GKE cluster."""
    try:
        project = project_id or settings.project_id
        client = container_v1.ClusterManagerClient()
        
        # First find the cluster location
        parent = f"projects/{project}/locations/-"
        response = client.list_clusters(parent=parent)
        
        target_cluster = None
        for cluster in response.clusters:
            if cluster.name == cluster_name:
                target_cluster = cluster
                break
        
        if not target_cluster:
            return {"error": f"Cluster {cluster_name} not found"}
        
        details = {
            "name": target_cluster.name,
            "status": str(target_cluster.status),
            "location": target_cluster.location,
            "endpoint": target_cluster.endpoint,
            "master_version": target_cluster.current_master_version,
            "node_version": target_cluster.current_node_version,
            "node_count": target_cluster.current_node_count,
            "create_time": str(target_cluster.create_time),
            "network": target_cluster.network,
            "subnetwork": target_cluster.subnetwork,
            "cluster_ipv4_cidr": target_cluster.cluster_ipv4_cidr,
            "services_ipv4_cidr": target_cluster.services_ipv4_cidr,
            "node_pools": [{"name": np.name, "node_count": np.initial_node_count} for np in target_cluster.node_pools] if target_cluster.node_pools else [],
            "labels": dict(target_cluster.resource_labels) if target_cluster.resource_labels else {}
        }
        
        logger.info(f"Retrieved details for GKE cluster: {cluster_name}")
        return details
    except Exception as e:
        logger.error(f"Error getting cluster details for {cluster_name}: {e}")
        return {"error": str(e)}
