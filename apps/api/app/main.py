from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.dashboard_router import router as dashboard_router
from app.routers.inspection_router import router as inspection_router
from app.routers.inventory_router import router as inventory_router
from app.routers.products_router import router as products_router
from app.routers.purchase_orders_router import router as purchase_orders_router
from app.routers.receiving_router import router as receiving_router
from app.routers.replenishment_router import router as replenishment_router
from app.routers.settings_router import router as settings_router
from app.routers.suppliers_router import router as suppliers_router


def create_app() -> FastAPI:
    app = FastAPI(title="ERP_DEMO API", version="0.1.0")

    app.include_router(dashboard_router)
    app.include_router(inspection_router)
    app.include_router(inventory_router)
    app.include_router(products_router)
    app.include_router(receiving_router)
    app.include_router(purchase_orders_router)
    app.include_router(replenishment_router)
    app.include_router(settings_router)
    app.include_router(suppliers_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
