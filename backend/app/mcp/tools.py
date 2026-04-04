from app.mcp.server import server, _json
import mcp.types as types
from app.gcp import vm, vpc, storage, gke, functions, billing, cloudsql, loadbalancer, dns

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        # ── VM ──────────────────────────────────────────────────
        types.Tool(name="list_vms",
            description="List all Compute Engine VMs across all zones.",
            inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
        types.Tool(name="get_vm_details",
            description="Get detailed info for a specific VM by name.",
            inputSchema={"type": "object", "properties": {"instance_name": {"type": "string"}}, "required": ["instance_name"]}),

        # ── VPC ─────────────────────────────────────────────────
        types.Tool(name="list_networks",
            description="List all VPC networks.",
            inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
        types.Tool(name="get_vpc_details",
            description="Get detailed info for a specific VPC network.",
            inputSchema={"type": "object", "properties": {"network_name": {"type": "string"}}, "required": ["network_name"]}),

        # ── Storage ─────────────────────────────────────────────
        types.Tool(name="list_buckets",
            description="List all Cloud Storage buckets.",
            inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
        types.Tool(name="get_bucket_details",
            description="Get detailed info for a specific bucket.",
            inputSchema={"type": "object", "properties": {"bucket_name": {"type": "string"}}, "required": ["bucket_name"]}),

        # ── GKE ─────────────────────────────────────────────────
        types.Tool(name="list_clusters",
            description="List all GKE Kubernetes clusters.",
            inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
        types.Tool(name="get_cluster_details",
            description="Get detailed info for a specific GKE cluster.",
            inputSchema={"type": "object", "properties": {"cluster_name": {"type": "string"}}, "required": ["cluster_name"]}),

        # ── Cloud Functions ──────────────────────────────────────
        types.Tool(name="list_functions",
            description="List all Cloud Functions.",
            inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
        types.Tool(name="get_function_details",
            description="Get detailed info for a specific Cloud Function.",
            inputSchema={"type": "object", "properties": {"function_name": {"type": "string"}}, "required": ["function_name"]}),

        # ── Billing ─────────────────────────────────────────────
        types.Tool(name="get_billing_info",
            description="Get project billing status and account info.",
            inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
        types.Tool(name="get_billing_history",
            description="Get budget/billing summary for the last N days.",
            inputSchema={"type": "object", "properties": {"days": {"type": "integer"}}}),

        # ── Cloud SQL ────────────────────────────────────────────
        types.Tool(name="list_sql_instances",
            description="List all Cloud SQL database instances.",
            inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
        types.Tool(name="get_sql_instance_details",
            description="Get detailed info for a specific Cloud SQL instance.",
            inputSchema={"type": "object", "properties": {"instance_name": {"type": "string"}}, "required": ["instance_name"]}),
        types.Tool(name="list_sql_databases",
            description="List all databases inside a Cloud SQL instance.",
            inputSchema={"type": "object", "properties": {"instance_name": {"type": "string"}}, "required": ["instance_name"]}),

        # ── Load Balancer ────────────────────────────────────────
        types.Tool(name="list_load_balancers",
            description="List all load balancers with URL maps, forwarding rules and backends.",
            inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),

        # ── DNS ──────────────────────────────────────────────────
        types.Tool(name="list_dns_zones",
            description="List all Cloud DNS zones.",
            inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
        types.Tool(name="get_dns_zone_details",
            description="Get detailed info and record sets for a specific DNS zone.",
            inputSchema={"type": "object", "properties": {"zone_name": {"type": "string"}}, "required": ["zone_name"]}),
        types.Tool(name="list_dns_records",
            description="List all DNS record sets inside a zone.",
            inputSchema={"type": "object", "properties": {"zone_name": {"type": "string"}}, "required": ["zone_name"]}),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    args = arguments or {}
    project_id = args.get("project_id")

    match name:
        # VM
        case "list_vms":           return _json(vm.list_vms(project_id=project_id))
        case "get_vm_details":     return _json(vm.get_vm_details(args["instance_name"], project_id=project_id))
        # VPC
        case "list_networks":      return _json(vpc.list_networks(project_id=project_id))
        case "get_vpc_details":    return _json(vpc.get_vpc_details(args["network_name"], project_id=project_id))
        # Storage
        case "list_buckets":       return _json(storage.list_buckets(project_id=project_id))
        case "get_bucket_details": return _json(storage.get_bucket_details(args["bucket_name"]))
        # GKE
        case "list_clusters":      return _json(gke.list_clusters(project_id=project_id))
        case "get_cluster_details":return _json(gke.get_cluster_details(args["cluster_name"], project_id=project_id))
        # Functions
        case "list_functions":     return _json(functions.list_functions(project_id=project_id))
        case "get_function_details":return _json(functions.get_function_details(args["function_name"], project_id=project_id))
        # Billing
        case "get_billing_info":   return _json(billing.get_billing_info(project_id=project_id))
        case "get_billing_history":return _json(billing.get_billing_history(args.get("days", 30)))
        # Cloud SQL
        case "list_sql_instances": return _json(cloudsql.list_instances(project_id=project_id))
        case "get_sql_instance_details": return _json(cloudsql.get_instance_details(args["instance_name"], project_id=project_id))
        case "list_sql_databases": return _json(cloudsql.list_databases(args["instance_name"], project_id=project_id))
        # Load Balancer
        case "list_load_balancers":return _json(loadbalancer.list_load_balancers(project_id=project_id))
        # DNS
        case "list_dns_zones":     return _json(dns.list_zones(project_id=project_id))
        case "get_dns_zone_details":return _json(dns.get_zone_details(args["zone_name"], project_id=project_id))
        case "list_dns_records":   return _json(dns.list_record_sets(args["zone_name"], project_id=project_id))
        case _:                    raise ValueError(f"Unknown tool: {name}")


async def run():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read, write):
        await server.run(
            read_stream=read,
            write_stream=write,
            initialization_options=server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(run())
