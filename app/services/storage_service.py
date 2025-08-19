import os
import uuid
from PIL import Image
import io
from app.config import get_settings
import base64
from typing import BinaryIO
from datetime import timedelta

settings = get_settings()

class StorageService:
    def __init__(self):
        self.settings = settings
        self.use_minio = False
        
        # Check if MinIO is available (not on Railway)
        try:
            if not self.settings.minio_endpoint.startswith("localhost"):
                from minio import Minio
                self.client = Minio(
                    self.settings.minio_endpoint,
                    access_key=self.settings.minio_access_key,
                    secret_key=self.settings.minio_secret_key,
                    secure=self.settings.minio_secure
                )
                self.bucket = self.settings.minio_bucket
                
                # Test connection
                self.client.list_buckets()
                self.use_minio = True
                print("✅ MinIO connection successful")
        except Exception as e:
            print(f"⚠️  MinIO not available, using fallback storage: {e}")
            self.use_minio = False
    
    def upload_image(self, file_data: bytes, filename: str) -> str:
        """Upload image to MinIO and return path"""
        if self.use_minio:
            return self._upload_to_minio(file_data, filename)
        else:
            return self._upload_fallback(file_data, filename)
    
    def _upload_to_minio(self, file_data: bytes, filename: str) -> str:
        """Upload to MinIO"""
        try:
            # Generate unique filename
            ext = filename.split('.')[-1] if '.' in filename else 'jpg'
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
        except Exception as e:
            print(f"MinIO upload failed: {e}")
            return self._upload_fallback(file_data, filename)
    
    def create_thumbnail(self, file_data: bytes, filename: str, size=(300, 300)) -> str:
        """Create and upload thumbnail"""
        try:
            # Open image
            img = Image.open(io.BytesIO(file_data))
            
            # Create thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            thumb_io = io.BytesIO()
            img.save(thumb_io, format='JPEG', quality=85)
            thumb_data = thumb_io.getvalue()
            
            if self.use_minio:
                return self._create_thumbnail_minio(thumb_data, filename)
            else:
                return self._upload_fallback(thumb_data, f"thumb_{filename}")
                
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            # Return original image path as fallback
            return self.upload_image(file_data, filename)
    
    def _create_thumbnail_minio(self, thumb_data: bytes, filename: str) -> str:
        """Upload thumbnail to MinIO"""
        try:
            # Upload thumbnail
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
        except Exception as e:
            print(f"Thumbnail upload to MinIO failed: {e}")
            return self._upload_fallback(thumb_data, f"thumb_{filename}")
    
    def get_image_url(self, path: str) -> str:
        """Get presigned URL for image"""
        if self.use_minio and not path.startswith("data:"):
            try:
                url = self.client.presigned_get_object(
                    self.bucket,
                    path,
                    expires=timedelta(hours=24)
                )
                return url
            except Exception as e:
                print(f"Error getting MinIO URL: {e}")
        
        # Fallback: return data URL or placeholder
        if path.startswith("data:"):
            return path
        else:
            # Return placeholder image URL
            return f"https://via.placeholder.com/300x200?text={os.path.basename(path)}"
    
    def delete_image(self, path: str):
        """Delete image from MinIO"""
        if self.use_minio and not path.startswith("data:"):
            try:
                self.client.remove_object(self.bucket, path)
            except Exception as e:
                print(f"Error deleting from MinIO: {e}")
    
    def _upload_fallback(self, file_data: bytes, filename: str) -> str:
        """Fallback storage - convert to data URL"""
        try:
            # Convert to base64 data URL for temporary storage
            content_type = self._get_content_type(filename)
            base64_data = base64.b64encode(file_data).decode('utf-8')
            data_url = f"data:{content_type};base64,{base64_data}"
            
            return data_url
            
        except Exception as e:
            print(f"Fallback storage failed: {e}")
            return f"error_{filename}"
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename"""
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return content_types.get(ext, 'image/jpeg')

storage_service = StorageService()