from fastapi import FastAPI
from app.routers.auth import auth_router
from app.routers.health import health_router

app = FastAPI(title="Health API", version="1.0.0")

app.include_router(auth_router)
app.include_router(health_router)


@app.get("/")
def root():
    return {"message": "Health API is running", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
