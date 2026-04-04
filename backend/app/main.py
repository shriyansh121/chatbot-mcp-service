import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional

from app.gcp import vm, vpc, storage, gke, functions, billing, cloudsql, loadbalancer, dns
from app.api import auth, chat
from app.services.cache_service import (
    preload_quick_action_cache,
    get_cached_vms,
    get_cached_networks,
    get_cached_buckets,
    get_cached_billing,
    cache_invalidate_all
)
from app.lib_helper.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle: preload caches on startup."""
    # Startup: preload quick action caches for fast responses
    await preload_quick_action_cache(project_id=settings.PROJECT_ID)
    yield
    # Shutdown: cleanup if needed
    pass


app = FastAPI(title="GCP Assistant API", version="2.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)


# ══════════════════════════════════════════════════════════════════════════════
# CACHED QUICK ACTION ENDPOINTS (Fast responses for the 4 main queries)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/quick/vms")
def quick_list_vms(project_id: Optional[str] = None):
    """List VMs with caching for fast response."""
    result = get_cached_vms(project_id)
    return {"data": result["data"], "cached": result["cached"]}


@app.get("/api/quick/networks")
def quick_list_networks(project_id: Optional[str] = None):
    """List VPC networks with caching for fast response."""
    result = get_cached_networks(project_id)
    return {"data": result["data"], "cached": result["cached"]}


@app.get("/api/quick/buckets")
def quick_list_buckets(project_id: Optional[str] = None):
    """List storage buckets with caching for fast response."""
    result = get_cached_buckets(project_id)
    return {"data": result["data"], "cached": result["cached"]}


@app.get("/api/quick/billing")
def quick_billing_summary(project_id: Optional[str] = None):
    """Get billing summary with caching for fast response."""
    result = get_cached_billing(project_id)
    return {"data": result["data"], "cached": result["cached"]}


@app.post("/api/quick/invalidate")
def invalidate_quick_cache():
    """Invalidate all quick action caches (force refresh on next request)."""
    cache_invalidate_all()
    return {"status": "ok", "message": "All quick action caches invalidated"}


# Mount static frontend files
frontend_dir = os.path.join(os.path.dirname(__file__), "../../frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        # Serve from frontend directory if exists
        file_path = os.path.join(frontend_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        # Otherwise return index for health check or routing
        return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/health")
def health():
    return {"status": "ok", "service": "gcp-assistant"}

# ── VM ──────────────────────────────────────────────────────────
@app.get("/api/vms")
def list_vms(project_id: Optional[str] = None):
    return vm.list_vms(project_id=project_id)

@app.get("/api/vms/{name}")
def get_vm(name: str, project_id: Optional[str] = None):
    return vm.get_vm_details(name, project_id=project_id)

# ── VPC ─────────────────────────────────────────────────────────
@app.get("/api/networks")
def list_networks(project_id: Optional[str] = None):
    return vpc.list_networks(project_id=project_id)

@app.get("/api/networks/{name}")
def get_network(name: str, project_id: Optional[str] = None):
    return vpc.get_vpc_details(name, project_id=project_id)

# ── Storage ──────────────────────────────────────────────────────
@app.get("/api/buckets")
def list_buckets(project_id: Optional[str] = None):
    return storage.list_buckets(project_id=project_id)

@app.get("/api/buckets/{name}")
def get_bucket(name: str):
    return storage.get_bucket_details(name)

# ── GKE ─────────────────────────────────────────────────────────
@app.get("/api/clusters")
def list_clusters(project_id: Optional[str] = None):
    return gke.list_clusters(project_id=project_id)

@app.get("/api/clusters/{name}")
def get_cluster(name: str, project_id: Optional[str] = None):
    return gke.get_cluster_details(name, project_id=project_id)

# ── Cloud Functions ───────────────────────────────────────────────
@app.get("/api/functions")
def list_functions(project_id: Optional[str] = None):
    return functions.list_functions(project_id=project_id)

@app.get("/api/functions/{name}")
def get_function(name: str, project_id: Optional[str] = None):
    return functions.get_function_details(name, project_id=project_id)

# ── Billing ───────────────────────────────────────────────────────
@app.get("/api/billing")
def get_billing(project_id: Optional[str] = None):
    return billing.get_billing_info(project_id=project_id)

@app.get("/api/billing/summary")
def billing_summary():
    return billing.get_billing_summary()

# ── Cloud SQL ─────────────────────────────────────────────────────
@app.get("/api/sql/instances")
def list_sql(project_id: Optional[str] = None):
    return cloudsql.list_instances(project_id=project_id)

@app.get("/api/sql/instances/{name}")
def get_sql(name: str, project_id: Optional[str] = None):
    return cloudsql.get_instance_details(name, project_id=project_id)

@app.get("/api/sql/instances/{name}/databases")
def list_dbs(name: str, project_id: Optional[str] = None):
    return cloudsql.list_databases(name, project_id=project_id)

# ── Load Balancer ─────────────────────────────────────────────────
@app.get("/api/loadbalancers")
def list_lbs(project_id: Optional[str] = None):
    return loadbalancer.list_load_balancers(project_id=project_id)

# ── DNS ───────────────────────────────────────────────────────────
@app.get("/api/dns/zones")
def list_zones(project_id: Optional[str] = None):
    return dns.list_zones(project_id=project_id)

@app.get("/api/dns/zones/{name}")
def get_zone(name: str, project_id: Optional[str] = None):
    return dns.get_zone_details(name, project_id=project_id)

@app.get("/api/dns/zones/{name}/records")
def list_records(name: str, project_id: Optional[str] = None):
    return dns.list_record_sets(name, project_id=project_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)