from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import numpy as np
from app.database import get_db
from app.models.image import EventImage, FaceVector
from app.services.storage_service import storage_service
from app.services.face_service import face_service
from app.workers.tasks import process_image_task
from pydantic import BaseModel

# Remove prefix here since it's added in main.py
router = APIRouter(tags=["images"])

class ImageResponse(BaseModel):
    id: int
    filename: str
    url: str
    thumbnail_url: str
    face_count: int

class SearchResponse(BaseModel):
    images: List[ImageResponse]
    total: int

@router.post("/images/upload")
async def upload_images(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload multiple images for processing"""
    uploaded = []
    
    for file in files:
        # Read file data
        file_data = await file.read()
        
        # Upload to storage
        image_path = storage_service.upload_image(file_data, file.filename)
        thumbnail_path = storage_service.create_thumbnail(file_data, file.filename)
        
        # Save to database
        db_image = EventImage(
            filename=file.filename,
            minio_path=image_path,
            thumbnail_path=thumbnail_path,
            face_count=0
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)
        
        # Process faces immediately (SYNC) for debugging
        try:
            print(f"🔍 Processing faces for image: {file.filename}")
            
            # Extract face encodings
            encodings = face_service.extract_face_encodings(file_data)
            print(f"📊 Found {len(encodings)} face encodings")
            
            if encodings:
                # Save face vectors
                for i, encoding in enumerate(encodings):
                    print(f"💾 Saving face vector {i+1}/{len(encodings)}")
                    face_vector = FaceVector(
                        image_id=db_image.id,
                        face_index=i,
                        encoding=encoding.tolist()  # Convert numpy array to list
                    )
                    db.add(face_vector)
                
                # Update face count
                db_image.face_count = len(encodings)
                db.commit()
                
                status = f"processed - {len(encodings)} faces found"
                print(f"✅ Successfully processed {len(encodings)} faces")
            else:
                status = "processed - no faces found"
                print("⚠️  No faces detected in image")
                
        except Exception as e:
            print(f"❌ Face processing error: {e}")
            import traceback
            traceback.print_exc()
            status = f"processing failed: {str(e)}"
        
        uploaded.append({
            "id": db_image.id,
            "filename": file.filename,
            "status": status,
            "face_count": db_image.face_count
        })
    
    return {"uploaded": uploaded}

@router.post("/images/search")
async def search_by_face(
    file: UploadFile = File(...),
    tolerance: float = Query(0.4, ge=0.1, le=1.0),  # Giảm tolerance mặc định
    db: Session = Depends(get_db)
):
    """Search images by face"""
    # Read search image
    file_data = await file.read()
    
    # Extract face encoding from search image
    success, query_encoding = face_service.process_search_image(file_data)
    
    if not success:
        raise HTTPException(status_code=400, detail="No face found in search image")
    
    # Get all face vectors from database
    all_vectors = db.query(FaceVector).all()
    
    # Store matches with distances for sorting
    matches = []
    
    for vector in all_vectors:
        # Convert stored vector to numpy array
        stored_encoding = np.array(vector.encoding)
        
        # Use face_recognition.compare_faces for better accuracy
        is_match = face_service.compare_single_face(query_encoding, stored_encoding, tolerance)
        
        if is_match:
            # Calculate distance for sorting
            distance = face_service.calculate_face_distance(query_encoding, stored_encoding)
            matches.append({
                'image_id': vector.image_id,
                'distance': distance
            })
    
    # Sort by distance (best matches first)
    matches.sort(key=lambda x: x['distance'])
    matching_image_ids = [m['image_id'] for m in matches]
    
    # Get matching images
    if matching_image_ids:
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for img_id in matching_image_ids:
            if img_id not in seen:
                seen.add(img_id)
                unique_ids.append(img_id)
        
        images = db.query(EventImage).filter(
            EventImage.id.in_(unique_ids)
        ).all()
        
        # Create dict for ordering
        image_dict = {img.id: img for img in images}
        ordered_images = [image_dict[img_id] for img_id in unique_ids if img_id in image_dict]
        
        # Prepare response
        results = []
        for img in ordered_images:
            results.append(ImageResponse(
                id=img.id,
                filename=img.filename,
                url=storage_service.get_image_url(img.minio_path),
                thumbnail_url=storage_service.get_image_url(img.thumbnail_path),
                face_count=img.face_count
            ))
        
        return SearchResponse(images=results, total=len(results))
    
    return SearchResponse(images=[], total=0)

@router.get("/images/all")
async def get_all_images(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all event images with pagination"""
    images = db.query(EventImage).offset(skip).limit(limit).all()
    total = db.query(EventImage).count()
    
    results = []
    for img in images:
        results.append(ImageResponse(
            id=img.id,
            filename=img.filename,
            url=storage_service.get_image_url(img.minio_path),
            thumbnail_url=storage_service.get_image_url(img.thumbnail_path),
            face_count=img.face_count
        ))
    
    return {
        "images": results,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/images/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get statistics"""
    total_images = db.query(EventImage).count()
    total_faces = db.query(FaceVector).count()
    images_with_faces = db.query(EventImage).filter(EventImage.face_count > 0).count()
    
    return {
        "total_images": total_images,
        "total_faces": total_faces,
        "images_with_faces": images_with_faces
    }

@router.get("/images/debug")
async def debug_info(db: Session = Depends(get_db)):
    """Debug endpoint to check processing"""
    # Get recent images
    recent_images = db.query(EventImage).order_by(EventImage.id.desc()).limit(5).all()
    
    # Get face vectors count
    face_vectors = db.query(FaceVector).all()
    
    return {
        "recent_images": [
            {
                "id": img.id,
                "filename": img.filename,
                "face_count": img.face_count,
                "minio_path": img.minio_path
            }
            for img in recent_images
        ],
        "total_face_vectors": len(face_vectors),
        "face_vectors_sample": [
            {
                "id": fv.id,
                "image_id": fv.image_id,
                "face_index": fv.face_index,
                "encoding_length": len(fv.encoding) if fv.encoding else 0
            }
            for fv in face_vectors[:5]
        ]
    }