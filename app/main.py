from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import images
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Event Images API")

# CORS middleware - updated for deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",  # Next.js dev server
        "https://face-search-frontend.vercel.app/",   # Vercel deployments
        "https://face-search-frontend.vercel.app/",
    ],
    allow_credentials=True,
    allow_methods=["*"],
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