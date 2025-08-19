from celery import Celery
from app.config import get_settings
from app.database import SessionLocal
from app.models.image import EventImage, FaceVector
from app.services.face_service import face_service
import numpy as np
import os

settings = get_settings()

# Get Redis URL from environment (Railway will auto-set this)
redis_url = os.getenv("REDIS_URL") or settings.redis_url

print(f"📡 Celery connecting to Redis: {redis_url}")

# Create Celery app
celery_app = Celery(
    'event_images',
    broker=redis_url,
    backend=redis_url
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # Add connection retry settings
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
)

@celery_app.task
def process_image_task(image_id: int, image_data_hex: str):
    """Process image to extract face encodings"""
    print(f"🔄 Processing image {image_id}...")
    
    db = SessionLocal()
    
    try:
        # Get image from database
        image = db.query(EventImage).filter(EventImage.id == image_id).first()
        if not image:
            print(f"❌ Image {image_id} not found")
            return {"error": "Image not found"}
        
        # Convert hex back to bytes
        image_data = bytes.fromhex(image_data_hex)
        print(f"📷 Processing {len(image_data)} bytes of image data")
        
        # Extract face encodings
        encodings = face_service.extract_face_encodings(image_data)
        print(f"👤 Found {len(encodings)} faces")
        
        if encodings:
            # Store encodings as JSON
            image.face_encodings = face_service.encodings_to_json(encodings)
            image.face_count = len(encodings)
            
            # Store each face as vector for searching
            for i, encoding in enumerate(encodings):
                face_vector = FaceVector(
                    image_id=image_id,
                    face_index=i,
                    encoding=encoding.tolist()
                )
                db.add(face_vector)
            
            db.commit()
            print(f"✅ Successfully processed image {image_id} with {len(encodings)} faces")
            
            return {
                "image_id": image_id,
                "faces_found": len(encodings),
                "status": "success"
            }
        else:
            # No faces found
            image.face_count = 0
            image.face_encodings = "[]"
            db.commit()
            print(f"⚠️  No faces found in image {image_id}")
            
            return {
                "image_id": image_id,
                "faces_found": 0,
                "status": "no_faces"
            }
            
    except Exception as e:
        db.rollback()
        print(f"❌ Error processing image {image_id}: {str(e)}")
        return {
            "image_id": image_id,
            "error": str(e),
            "status": "error"
        }
    finally:
        db.close()