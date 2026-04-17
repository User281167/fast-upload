from fastapi import FastAPI

from server.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="Fast Upload Server")
    app.include_router(router)
    return app


app = create_app()
