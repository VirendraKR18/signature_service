import os
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image
import fitz  # PyMuPDF

from .config import settings

logger = logging.getLogger(__name__)


class SignatureDetectionService:
    
    def __init__(self):
        self.model = None
        self.model_path = settings.MODEL_PATH
        self.temp_dir = None
        
    def _load_model(self):
        if self.model is not None:
            return

        # On Render, skip YOLO (no PyTorch installed to save memory)
        if settings.IS_RENDER:
            logger.info("Render deployment — YOLO skipped, using OCR-based detection")
            self.model = None
            return
            
        try:
            from ultralytics import YOLO
            
            if os.path.exists(self.model_path):
                self.model = YOLO(self.model_path)
                logger.info(f"YOLO model loaded from {self.model_path}")
            else:
                logger.warning(f"YOLO model not found at {self.model_path}")
                self.model = None
        except ImportError:
            logger.warning("ultralytics package not installed")
            self.model = None
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        self._load_model()
        return self.model is not None
    
    def get_status(self) -> Dict:
        model_exists = os.path.exists(self.model_path)
        return {
            "available": self.is_available(),
            "model_path": self.model_path,
            "model_exists": model_exists
        }
    
    def _convert_pdf_to_images(self, pdf_path: str) -> List[Tuple[int, str]]:
        self.temp_dir = tempfile.mkdtemp()
        page_images = []
        
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Render at 150 DPI for good quality
                mat = fitz.Matrix(150/72, 150/72)
                pix = page.get_pixmap(matrix=mat)
                image_path = os.path.join(self.temp_dir, f"page_{page_num + 1}.jpg")
                pix.save(image_path)
                page_images.append((page_num + 1, image_path))
                logger.info(f"Converted page {page_num + 1} to {image_path} using PyMuPDF")
            doc.close()
            return page_images
        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            self._cleanup_temp_dir()
            raise
    
    def _detect_signatures_in_image(self, image_path: str) -> Tuple[List[Dict], Tuple[int, int]]:
        if self.model is None:
            return [], (0, 0)
        
        try:
            # Get image dimensions
            img = Image.open(image_path)
            img_width, img_height = img.size
            
            results = self.model(image_path)
            
            boxes = []
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        confidence = float(box.conf[0])
                        
                        boxes.append({
                            "x1": int(x1),
                            "y1": int(y1),
                            "x2": int(x2),
                            "y2": int(y2),
                            "confidence": round(confidence, 2)
                        })
            
            return boxes, (img_width, img_height)
            
        except Exception as e:
            logger.error(f"Failed to detect signatures in {image_path}: {e}")
            return [], (0, 0)
    
    def _cleanup_temp_dir(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup temp directory: {e}")
            finally:
                self.temp_dir = None
    
    def detect_signatures(self, pdf_path: str) -> Dict:
        if not self.is_available():
            raise Exception("Signature detection model not available")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            page_images = self._convert_pdf_to_images(pdf_path)
            
            boxes_by_page = {}
            page_dimensions = {}
            pages_with_signatures = 0
            
            for page_num, image_path in page_images:
                boxes, (img_width, img_height) = self._detect_signatures_in_image(image_path)
                
                # Store dimensions for each page
                page_dimensions[str(page_num)] = {
                    "width": img_width,
                    "height": img_height
                }
                
                if boxes:
                    boxes_by_page[str(page_num)] = boxes
                    pages_with_signatures += 1
                    logger.info(f"Page {page_num}: Found {len(boxes)} signature(s)")
            
            self._cleanup_temp_dir()
            
            return {
                "status": "success",
                "boxesByPage": boxes_by_page,
                "pageDimensions": page_dimensions,
                "total_pages": len(page_images),
                "pages_with_signatures": pages_with_signatures
            }
            
        except Exception as e:
            self._cleanup_temp_dir()
            logger.error(f"Signature detection failed: {e}")
            raise


signature_detection_service = SignatureDetectionService()
