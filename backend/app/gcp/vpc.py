from google.cloud import compute_v1
from app.lib.config import settings
from app.lib.logger import setup_logger

logger = setup_logger("gcp.vpc")

def list_networks(project_id: str = None):
    """Lists all VPC networks in the project."""
    try:
        project = project_id or settings.project_id
        client = compute_v1.NetworksClient()
        request = compute_v1.ListNetworksRequest(project=project)
        
        response = client.list(request=request)
        
        networks = []
        for network in response:
            networks.append({
                "name": network.name,
                "auto_create_subnetworks": network.auto_create_subnetworks,
                "creation_timestamp": network.creation_timestamp,
                "subnetworks": [sub.split("/")[-1] for sub in network.subnetworks] if network.subnetworks else [],
                "mtu": network.mtu
            })
            
        logger.info(f"Listed {len(networks)} VPC networks in project {project}.")
        return networks
    except Exception as e:
        logger.error(f"Error listing networks: {e}")
        return []

def get_vpc_details(network_name: str, project_id: str = None):
    """Gets detailed information for a specific VPC network."""
    try:
        project = project_id or settings.project_id
        client = compute_v1.NetworksClient()
        request = compute_v1.GetNetworkRequest(
            project=project,
            network=network_name
        )
        
        network = client.get(request=request)
        
        details = {
            "name": network.name,
            "id": str(network.id),
            "self_link": network.self_link,
            "auto_create_subnetworks": network.auto_create_subnetworks,
            "creation_timestamp": network.creation_timestamp,
            "mtu": network.mtu,
            "routing_config": {
                "routing_mode": str(network.routing_config.routing_mode) if network.routing_config else "N/A"
            },
            "subnetworks": [sub.split("/")[-1] for sub in network.subnetworks] if network.subnetworks else [],
            "peerings": [{"name": p.name, "network": p.network.split("/")[-1]} for p in network.peerings] if network.peerings else []
        }
        
        logger.info(f"Retrieved details for VPC: {network_name}")
        return details
    except Exception as e:
        logger.error(f"Error getting VPC details for {network_name}: {e}")
        return {"error": str(e)}

import json
print("=" * 60)
print("Listing all VPCs using vertex-ai.json credentials...")
print("=" * 60)
all_vms = list_networks()
if all_vms:
    print(json.dumps(all_vms, indent=2))
    print(f"\nTotal VPCs found: {len(all_vms)}")
    # Example: get details of the first VM
    first = all_vms[1]
    print(f"\n{'=' * 60}")
    print(f"Getting details for: ",first['name'])
    print(f"{'=' * 60}")
    details = get_vpc_details(network_name="gcp-network", project_id="devops-internal-439011")
    print(json.dumps(details, indent=2))
else:
    print("No VMs found (or auth failed — check logs).")