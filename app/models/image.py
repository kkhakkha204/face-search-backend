from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base

class EventImage(Base):
    __tablename__ = "event_images"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, nullable=False)
    minio_path = Column(String, nullable=False)
    thumbnail_path = Column(String)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Face encodings - store multiple faces per image
    face_count = Column(Integer, default=0)
    face_encodings = Column(Text)  # JSON array of face encodings
    
class FaceVector(Base):
    __tablename__ = "face_vectors"
    
    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, index=True)
    face_index = Column(Integer)  # Index of face in the image
    encoding = Column(Vector(128))  # face_recognition uses 128-dimensional vectors
    created_at = Column(DateTime(timezone=True), server_default=func.now())