import cv2
import numpy as np
import mediapipe as mp
from typing import List, Tuple
import io
from PIL import Image
import json
import logging

logger = logging.getLogger(__name__)

class FaceService:
    def __init__(self):
        # Initialize MediaPipe Face Detection and Face Mesh
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        
        # Face detection model
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1,  # 0 for short range, 1 for long range
            min_detection_confidence=0.5
        )
        
        # Face mesh for landmarks (used for embeddings)
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=10,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    
    def extract_face_encodings(self, image_data: bytes) -> List[np.ndarray]:
        """Extract all face encodings from an image"""
        try:
            # Convert bytes to PIL Image
            pil_image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to numpy array
            image = np.array(pil_image)
            
            # Detect faces
            results = self.face_detection.process(image)
            
            encodings = []
            if results.detections:
                for detection in results.detections:
                    # Get bounding box
                    bbox = detection.location_data.relative_bounding_box
                    h, w, _ = image.shape
                    
                    # Convert to absolute coordinates
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)
                    
                    # Ensure coordinates are within image bounds
                    x = max(0, x)
                    y = max(0, y)
                    width = min(width, w - x)
                    height = min(height, h - y)
                    
                    # Extract face ROI
                    face_roi = image[y:y+height, x:x+width]
                    
                    # Generate embedding
                    embedding = self._generate_face_embedding(face_roi)
                    
                    if embedding is not None:
                        encodings.append(embedding)
            
            return encodings
            
        except Exception as e:
            logger.error(f"Error extracting face encodings: {str(e)}")
            return []
    
    def _generate_face_embedding(self, face_roi: np.ndarray) -> np.ndarray:
        """Generate face embedding from face ROI using face landmarks"""
        try:
            if face_roi.size == 0:
                return None
                
            # Get face mesh landmarks
            results = self.face_mesh.process(face_roi)
            
            if results.multi_face_landmarks:
                # Take the first face
                face_landmarks = results.multi_face_landmarks[0]
                
                # Convert landmarks to numpy array
                landmarks = []
                for landmark in face_landmarks.landmark:
                    landmarks.extend([landmark.x, landmark.y, landmark.z])
                
                # Convert to numpy array and normalize
                embedding = np.array(landmarks, dtype=np.float32)
                
                # Normalize the embedding
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                
                return embedding
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating face embedding: {str(e)}")
            return None
    
    def compare_single_face(self, query_encoding: np.ndarray, 
                           stored_encoding: np.ndarray, 
                           tolerance: float = 0.4) -> bool:
        """Compare two face encodings with stricter tolerance"""
        try:
            distance = self.calculate_face_distance(query_encoding, stored_encoding)
            return distance <= tolerance
        except Exception as e:
            logger.error(f"Error comparing faces: {str(e)}")
            return False
    
    def find_matching_faces(self, query_encoding: np.ndarray, 
                           stored_encodings: List[np.ndarray], 
                           tolerance: float = 0.6) -> List[int]:
        """Find matching faces from stored encodings"""
        if not stored_encodings:
            return []
        
        matching_indices = []
        for i, stored_encoding in enumerate(stored_encodings):
            if self.compare_single_face(query_encoding, stored_encoding, tolerance):
                matching_indices.append(i)
        
        return matching_indices
    
    def calculate_face_distance(self, encoding1: np.ndarray, 
                               encoding2: np.ndarray) -> float:
        """Calculate distance between two face encodings using cosine distance"""
        try:
            # Calculate cosine similarity
            dot_product = np.dot(encoding1, encoding2)
            norm1 = np.linalg.norm(encoding1)
            norm2 = np.linalg.norm(encoding2)
            
            if norm1 == 0 or norm2 == 0:
                return 1.0
            
            cosine_similarity = dot_product / (norm1 * norm2)
            
            # Convert to distance (1 - similarity)
            distance = 1 - cosine_similarity
            
            return float(distance)
            
        except Exception as e:
            logger.error(f"Error calculating distance: {str(e)}")
            return 1.0
    
    def encodings_to_json(self, encodings: List[np.ndarray]) -> str:
        """Convert face encodings to JSON string for storage"""
        if not encodings:
            return "[]"
        
        encodings_list = [encoding.tolist() for encoding in encodings]
        return json.dumps(encodings_list)
    
    def json_to_encodings(self, json_str: str) -> List[np.ndarray]:
        """Convert JSON string back to face encodings"""
        if not json_str or json_str == "[]":
            return []
        
        try:
            encodings_list = json.loads(json_str)
            return [np.array(encoding, dtype=np.float32) for encoding in encodings_list]
        except Exception as e:
            logger.error(f"Error converting JSON to encodings: {str(e)}")
            return []
    
    def process_search_image(self, image_data: bytes) -> Tuple[bool, np.ndarray]:
        """Process uploaded search image and extract face encoding"""
        encodings = self.extract_face_encodings(image_data)
        
        if not encodings:
            return False, None
        
        # Use first face found
        return True, encodings[0]

# Global instance
face_service = FaceService()