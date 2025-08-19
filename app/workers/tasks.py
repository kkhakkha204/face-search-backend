from celery import Celery
from app.config import get_settings
from app.database import SessionLocal
from app.models.image import EventImage, FaceVector
from app.services.face_service import face_service
import numpy as np

settings = get_settings()

# Create Celery app
celery_app = Celery(
    'event_images',
    broker=settings.redis_url,
    backend=settings.redis_url
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.task
def process_image_task(image_id: int, image_data_hex: str):
    """Process image to extract face encodings"""
    db = SessionLocal()
    
    try:
        # Get image from database
        image = db.query(EventImage).filter(EventImage.id == image_id).first()
        if not image:
            return {"error": "Image not found"}
        
        # Convert hex back to bytes
        image_data = bytes.fromhex(image_data_hex)
        
        # Extract face encodings
        encodings = face_service.extract_face_encodings(image_data)
        
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
            
            return {
                "image_id": image_id,
                "faces_found": len(encodings),
                "status": "success"
            }
        else:
            # No faces found
            image.face_count = 0
            db.commit()
            
            return {
                "image_id": image_id,
                "faces_found": 0,
                "status": "no_faces"
            }
            
    except Exception as e:
        db.rollback()
        return {
            "image_id": image_id,
            "error": str(e),
            "status": "error"
        }
    finally:
        db.close()