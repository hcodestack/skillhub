"""Module registry — add or remove a feature module by editing MODULES only.
Each module exposes a FastAPI `router`."""
from . import library, ingest, skills, health, hosts, mcp, report, sources, vetting

MODULES = [library, ingest, skills, health, hosts, mcp, report, sources, vetting]


def get_routers():
    return [m.router for m in MODULES]
