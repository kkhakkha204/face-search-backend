from minio import Minio
from app.config import get_settings
import io
from PIL import Image
import uuid
from typing import BinaryIO

settings = get_settings()

class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket = settings.minio_bucket
    
    def upload_image(self, file_data: bytes, filename: str) -> str:
        """Upload image to MinIO and return path"""
        # Generate unique filename
        ext = filename.split('.')[-1]
        unique_name = f"{uuid.uuid4()}.{ext}"
        path = f"images/{unique_name}"
        
        # Upload to MinIO
        self.client.put_object(
            self.bucket,
            path,
            io.BytesIO(file_data),
            len(file_data),
            content_type=f"image/{ext}"
        )
        
        return path
    
    def create_thumbnail(self, file_data: bytes, filename: str, size=(300, 300)) -> str:
        """Create and upload thumbnail"""
        # Open image
        img = Image.open(io.BytesIO(file_data))
        
        # Create thumbnail
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Save to bytes
        thumb_io = io.BytesIO()
        img.save(thumb_io, format='JPEG', quality=85)
        thumb_data = thumb_io.getvalue()
        
        # Upload thumbnail
        ext = filename.split('.')[-1]
        unique_name = f"{uuid.uuid4()}_thumb.jpg"
        path = f"thumbnails/{unique_name}"
        
        self.client.put_object(
            self.bucket,
            path,
            io.BytesIO(thumb_data),
            len(thumb_data),
            content_type="image/jpeg"
        )
        
        return path
    
    def get_image_url(self, path: str) -> str:
        """Get presigned URL for image"""
        from datetime import timedelta
        url = self.client.presigned_get_object(
            self.bucket,
            path,
            expires=timedelta(hours=24)
        )
        return url
    
    def delete_image(self, path: str):
        """Delete image from MinIO"""
        self.client.remove_object(self.bucket, path)

storage_service = StorageService()