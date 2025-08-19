import face_recognition
import numpy as np
from typing import List, Tuple
import io
from PIL import Image
import json

class FaceService:
    def extract_face_encodings(self, image_data: bytes) -> List[np.ndarray]:
        """Extract all face encodings from an image"""
        # Load image
        image = face_recognition.load_image_file(io.BytesIO(image_data))
        
        # Find all face encodings
        face_encodings = face_recognition.face_encodings(image)
        
        return face_encodings
    
    def compare_single_face(self, query_encoding: np.ndarray, 
                           stored_encoding: np.ndarray, 
                           tolerance: float = 0.4) -> bool:
        """Compare two face encodings with stricter tolerance"""
        # Use face_recognition's compare_faces for single comparison
        result = face_recognition.compare_faces(
            [stored_encoding], 
            query_encoding, 
            tolerance=tolerance
        )
        return result[0] if result else False
    
    def find_matching_faces(self, query_encoding: np.ndarray, 
                           stored_encodings: List[np.ndarray], 
                           tolerance: float = 0.6) -> List[int]:
        """Find matching faces from stored encodings"""
        if not stored_encodings:
            return []
        
        # Compare faces
        matches = face_recognition.compare_faces(
            stored_encodings, 
            query_encoding, 
            tolerance=tolerance
        )
        
        # Get indices of matches
        matching_indices = [i for i, match in enumerate(matches) if match]
        
        return matching_indices
    
    def calculate_face_distance(self, encoding1: np.ndarray, 
                               encoding2: np.ndarray) -> float:
        """Calculate distance between two face encodings"""
        return face_recognition.face_distance([encoding1], encoding2)[0]
    
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
        
        encodings_list = json.loads(json_str)
        return [np.array(encoding) for encoding in encodings_list]
    
    def process_search_image(self, image_data: bytes) -> Tuple[bool, np.ndarray]:
        """Process uploaded search image and extract face encoding"""
        encodings = self.extract_face_encodings(image_data)
        
        if not encodings:
            return False, None
        
        # Use first face found
        return True, encodings[0]

face_service = FaceService()