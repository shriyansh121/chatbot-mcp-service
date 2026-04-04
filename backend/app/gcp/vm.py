from google.cloud import compute_v1
from app.lib_helper.config import settings
from app.lib_helper.logger import setup_logger

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

def get_vm_details(instance_name: str, project_id: str = None):
    """Gets detailed information for a specific VM."""
    try:
        project = project_id or settings.project_id
        client = compute_v1.InstancesClient()
        request = compute_v1.AggregatedListInstancesRequest(project=project)
        agg_list = client.aggregated_list(request=request)
        
        for _, response in agg_list:
            if response.instances:
                for instance in response.instances:
                    if instance.name == instance_name:
                        vm = compute_v1.Instance.to_dict(instance)
                        details = {
                            "name": vm.get("name"),
                            "id": str(vm.get("id")),
                            "status": vm.get("status"),
                            "machine_type": vm.get("machine_type", "").split("/")[-1] if vm.get("machine_type") else "N/A",
                            "zone": vm.get("zone", "").split("/")[-1] if vm.get("zone") else "N/A",
                            "creation_timestamp": vm.get("creation_timestamp"),
                            "tags": vm.get("tags", {}).get("items", []),
                            "labels": vm.get("labels", {}),
                            "network": vm.get("network_interfaces", [{}])[0].get("network", "").split("/")[-1] if vm.get("network_interfaces") else "N/A",
                            "internal_ip": vm.get("network_interfaces", [{}])[0].get("network_ip", "N/A") if vm.get("network_interfaces") else "N/A",
                            "external_ip": vm.get("network_interfaces", [{}])[0].get("access_configs", [{}])[0].get("nat_ip", "N/A") if vm.get("network_interfaces") and vm.get("network_interfaces", [{}])[0].get("access_configs") else "N/A",
                            "disk_size_gb": vm.get("disks", [{}])[0].get("disk_size_gb", "N/A") if vm.get("disks") else "N/A"
                        }
                        logger.info(f"Retrieved details for VM: {instance_name}")
                        return details
        
        return {"error": f"VM {instance_name} not found"}
    except Exception as e:
        logger.error(f"Error getting VM details for {instance_name}: {e}")
        return {"error": str(e)}

# if __name__ == "__main__":
#     import json
#     print("=" * 60)
#     print("Listing all VMs using vertex-ai.json credentials...")
#     print("=" * 60)
#     all_vms = list_vms()
#     if all_vms:
#         #print(json.dumps(all_vms, indent=2))
#         #print(f"\nTotal VMs found: {len(all_vms)}")
#         # Example: get details of the first VM
#         first = all_vms[2]
#         print(f"\n{'=' * 60}")
#         print(f"Getting details for: {first['name']} in {first['zone']}")
#         print(f"{'=' * 60}")
#         details = get_vm_details(instance_name="voxilink-dev", project_id="devops-internal-439011")
#         print(json.dumps(details, indent=2))
#     else:
#         print("No VMs found (or auth failed — check logs).")