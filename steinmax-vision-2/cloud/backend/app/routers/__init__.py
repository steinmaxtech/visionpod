"""API routers."""

from app.routers.properties import router as properties_router
from app.routers.devices import router as devices_router
from app.routers.plates import router as plates_router
from app.routers.events import router as events_router
from app.routers.webhooks import router as webhooks_router
from app.routers.sync import router as sync_router

__all__ = [
    "properties_router",
    "devices_router", 
    "plates_router",
    "events_router",
    "webhooks_router",
    "sync_router",
]
