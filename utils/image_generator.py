"""Image generation utility using Google's Imagen API (WHISK)."""
import os
import logging
import base64
from typing import List, Optional, Dict
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()
logger = logging.getLogger(__name__)


class ImageGenerator:
    """Generate images using Google's Imagen API (WHISK)."""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        from config import GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS
        self.project_id = GOOGLE_CLOUD_PROJECT
        self.credentials_path = GOOGLE_APPLICATION_CREDENTIALS
        
    def generate_images(self, prompt: str, num_images: int = 3) -> List[Optional[Dict]]:
        """
        Generate images from a text prompt using Imagen 3 (via Vertex AI).
        
        Args:
            prompt: Text description of the image to generate
            num_images: Number of images to generate (default: 3)
            
        Returns:
            List of dicts with 'image_path' and 'image_bytes' or None if failed
        """
        if not self.project_id:
            logger.error("GOOGLE_CLOUD_PROJECT not configured in .env file")
            return [None] * num_images
        
        try:
            # Try to import Vertex AI
            try:
                import vertexai
                from vertexai.preview import generative_models
            except ImportError:
                logger.error("Vertex AI not installed. Run: pip install google-cloud-aiplatform")
                return [None] * num_images
            
            # Initialize Vertex AI
            try:
                vertexai.init(
                    project=self.project_id,
                    location="us-central1"  # Imagen is available in us-central1
                )
                logger.info(f"Initialized Vertex AI with project: {self.project_id}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Vertex AI initialization failed: {error_msg}")
                if "permission" in error_msg.lower() or "403" in error_msg:
                    logger.error("Make sure Vertex AI API is enabled and service account has proper permissions")
                elif "billing" in error_msg.lower():
                    logger.error("Billing may need to be enabled for your Google Cloud project")
                return [None] * num_images
            
            logger.info(f"Generating {num_images} images with prompt: {prompt[:50]}...")
            
            # Use Imagen API (different from GenerativeModel)
            try:
                from vertexai.preview.vision_models import ImageGenerationModel
                model = ImageGenerationModel.from_pretrained("imagegeneration@006")
            except ImportError:
                # Try alternative import path
                try:
                    from vertexai.vision_models import ImageGenerationModel
                    model = ImageGenerationModel.from_pretrained("imagegeneration@006")
                except Exception as e:
                    logger.error(f"Failed to import ImageGenerationModel: {e}")
                    logger.error("Make sure you have the latest google-cloud-aiplatform installed")
                    return [None] * num_images
            except Exception as e:
                logger.error(f"Failed to load Imagen model: {e}")
                logger.error("Make sure Imagen API is enabled in your Google Cloud project")
                return [None] * num_images
            
            generated_images = []
            output_dir = Path("outputs/generated_images")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate images
            for i in range(num_images):
                try:
                    response = model.generate_images(
                        prompt=prompt,
                        number_of_images=1,
                        aspect_ratio="1:1",  # Square for logos
                        safety_filter_level="block_some"
                        # Note: person_generation parameter removed as it's not available
                    )
                    
                    if response and hasattr(response, 'images') and response.images:
                        image = response.images[0]
                        # Save image
                        image_path = output_dir / f"logo_{i+1}_{hash(prompt) % 10000}.png"
                        
                        # Convert to PIL Image and save
                        if hasattr(image, 'image_bytes'):
                            img_bytes = image.image_bytes
                            pil_image = Image.open(io.BytesIO(img_bytes))
                            pil_image.save(image_path)
                            
                            generated_images.append({
                                "image_path": str(image_path),
                                "image_bytes": img_bytes,
                                "index": i
                            })
                            logger.info(f"Successfully generated image {i+1}")
                        elif hasattr(image, '_image_bytes'):
                            # Alternative attribute name
                            img_bytes = image._image_bytes
                            pil_image = Image.open(io.BytesIO(img_bytes))
                            pil_image.save(image_path)
                            
                            generated_images.append({
                                "image_path": str(image_path),
                                "image_bytes": img_bytes,
                                "index": i
                            })
                            logger.info(f"Successfully generated image {i+1}")
                        elif hasattr(image, '_pil_image'):
                            # Sometimes it's already a PIL image
                            pil_image = image._pil_image
                            pil_image.save(image_path)
                            
                            generated_images.append({
                                "image_path": str(image_path),
                                "image_bytes": None,  # Will read from file if needed
                                "index": i
                            })
                            logger.info(f"Successfully generated image {i+1}")
                        else:
                            logger.warning(f"Image {i+1} doesn't have expected attributes. Available: {[a for a in dir(image) if not a.startswith('__')]}")
                            generated_images.append(None)
                    else:
                        logger.warning(f"No images returned for generation {i+1}")
                        generated_images.append(None)
                        
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error generating image {i+1}: {error_msg}")
                    if "quota" in error_msg.lower() or "429" in error_msg:
                        logger.error("API quota exceeded. Please try again later.")
                    elif "permission" in error_msg.lower() or "403" in error_msg:
                        logger.error("Permission denied. Check service account permissions.")
                    elif "billing" in error_msg.lower():
                        logger.error("Billing may need to be enabled.")
                    elif "not found" in error_msg.lower() or "404" in error_msg:
                        logger.error("Imagen model not found. Make sure Imagen API is enabled and you have access.")
                    generated_images.append(None)
            
            return generated_images
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating images: {error_msg}")
            return [None] * num_images


def generate_logo_images(prompt: str, num_images: int = 3) -> List[Optional[Dict]]:
    """
    Generate logo images from a prompt.
    
    Args:
        prompt: Description of the logo
        num_images: Number of variations to generate
        
    Returns:
        List of dicts with image data or None if failed
    """
    generator = ImageGenerator()
    return generator.generate_images(prompt, num_images)

