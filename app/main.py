from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import images
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Event Images API")

# CORS middleware - updated for deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=False,  # Set to False when using "*"
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(images.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Event Images API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)