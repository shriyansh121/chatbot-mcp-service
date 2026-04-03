from google.cloud import compute_v1
from app.lib.config import settings
from app.lib.logger import setup_logger

logger = setup_logger("gcp.vm")

def list_vms(project_id: str = None):
    """Lists all VMs in the project across ALL zones."""
    try:
        project = project_id or settings.project_id
        client = compute_v1.InstancesClient()
        request = compute_v1.AggregatedListInstancesRequest(project=project)
        agg_list = client.aggregated_list(request=request)

        vms = []
        for _, response in agg_list:
            if response.instances:
                vms.extend([compute_v1.Instance.to_dict(i) for i in response.instances])
            
        # Extract key fields only
        result = []
        for vm in vms:
            result.append({
                "name": vm.get("name"),
                "status": vm.get("status"),
                "zone": vm.get("zone", "").split("/")[-1] if vm.get("zone") else "N/A",
                "creation_timestamp": vm.get("creation_timestamp"),
                "machine_type": vm.get("machine_type", "").split("/")[-1] if vm.get("machine_type") else "N/A",
                "internal_ip": vm.get("network_interfaces", [{}])[0].get("network_ip", "N/A") if vm.get("network_interfaces") else "N/A",
                "external_ip": vm.get("network_interfaces", [{}])[0].get("access_configs", [{}])[0].get("nat_ip", "N/A") if vm.get("network_interfaces") and vm.get("network_interfaces", [{}])[0].get("access_configs") else "N/A",
            })
        
        logger.info(f"Listed {len(result)} VMs across all zones in project {project}.")
        return result
    except Exception as e:
        logger.error(f"Error listing VMs: {e}")
        return []