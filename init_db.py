from app.database import engine, Base
from app.models.image import EventImage, FaceVector
from app.config import get_settings
from sqlalchemy import text
import os

def init_database():
    print("Creating database tables...")
    try:
        # Test connection first
        with engine.connect() as conn:
            print("✅ Database connection successful!")
            
            # Create vector extension if not exists
            print("📦 Creating vector extension...")
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                print("✅ Vector extension created successfully!")
            except Exception as e:
                print(f"⚠️  Vector extension warning: {e}")
                # Continue anyway, might already exist
        
        print("📋 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        # Verify tables created
        with engine.connect() as conn:
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"))
            tables = [row[0] for row in result]
            print(f"📋 Created tables: {tables}")
        
    except Exception as e:
        print(f"❌ Error with database: {e}")
        print("⚠️  Skipping database initialization - will retry later")
        # Don't crash the app, just continue without DB init
        pass

def init_minio():
    settings = get_settings()
    
    # Skip MinIO initialization on Railway
    railway_url = os.getenv("RAILWAY_STATIC_URL", "")
    if "railway.app" in railway_url or not settings.minio_endpoint or settings.minio_endpoint == "localhost:9000":
        print("⚠️  Skipping MinIO initialization on Railway deployment")
        return
    
    try:
        from minio import Minio
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        
        bucket_name = settings.minio_bucket
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"Created MinIO bucket: {bucket_name}")
        else:
            print(f"MinIO bucket already exists: {bucket_name}")
    except Exception as e:
        print(f"⚠️  MinIO initialization skipped: {e}")

if __name__ == "__main__":
    init_database()
    init_minio()