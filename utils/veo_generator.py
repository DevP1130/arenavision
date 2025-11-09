"""Video generation utility using Google's Veo 3.1 API."""
import os
import logging
from typing import Optional, Dict
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class VeoGenerator:
    """Generate videos using Google's Veo 3.1 API."""
    
    def __init__(self):
        from config import GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS
        self.project_id = GOOGLE_CLOUD_PROJECT
        self.credentials_path = GOOGLE_APPLICATION_CREDENTIALS
        
    def generate_intro_video(self, text: str, background_description: str, max_duration: int = 5, logo_path: Optional[str] = None) -> Optional[Dict]:
        """
        Generate an intro video using Veo 3.1.
        
        Args:
            text: Text to display on the video (centered)
            background_description: Description of the background to generate/create
            max_duration: Maximum duration in seconds (default: 5)
            logo_path: Optional path to logo image to overlay
            
        Returns:
            Dict with 'video_path' and metadata, or None if failed
        """
        try:
            import time
            from google import genai
            from google.genai import types
            import os
            
            # Initialize Google GenAI client
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.error("GOOGLE_API_KEY not configured in .env file")
                return self._create_placeholder_video(text, background_description, max_duration)
            
            client = genai.Client(api_key=api_key)
            
            logger.info(f"Generating intro video with text: '{text[:50]}...' and background: '{background_description[:50]}...'")
            
            output_dir = Path("outputs/generated_videos")
            output_dir.mkdir(parents=True, exist_ok=True)
            video_path = output_dir / f"intro_{hash(text + background_description) % 10000}.mp4"
            
            # Create enhanced prompt combining text and background
            enhanced_prompt = f"""Create a {max_duration}-second cinematic animated intro video.
Background: {background_description}
Text overlay (centered): {text}
Style: Modern, energetic, sports highlight intro with smooth animations, dynamic camera movements, and engaging visual effects.
Make it exciting and professional like a sports broadcast intro."""
            
            try:
                # Use Veo 3.0 API
                logger.info("Calling Veo 3.0 API...")
                operation = client.models.generate_videos(
                    model="veo-3.0-generate-001",
                    prompt=enhanced_prompt,
                    generation_config=types.GenerateVideosConfig(
                        aspect_ratio="16:9",
                        duration_seconds=max_duration,
                        temperature=0.7,
                        top_p=0.9
                    )
                )
                
                # Wait for operation to complete
                logger.info("Waiting for video generation to complete...")
                while not operation.done:
                    time.sleep(10)
                    operation = client.operations.get(operation)
                    logger.info("Still generating...")
                
                # Get the generated video
                if hasattr(operation, 'result') and operation.result:
                    if hasattr(operation.result, 'generated_videos') and operation.result.generated_videos:
                        generated_video = operation.result.generated_videos[0]
                        
                        # Download the video
                        if hasattr(generated_video, 'video'):
                            video_file = generated_video.video
                            video_data = client.files.download(file=video_file)
                            
                            # Save video to file
                            with open(video_path, 'wb') as f:
                                if hasattr(video_data, 'read'):
                                    f.write(video_data.read())
                                elif isinstance(video_data, bytes):
                                    f.write(video_data)
                                else:
                                    # Try to get bytes from response
                                    f.write(bytes(video_data))
                            
                            logger.info(f"Successfully generated Veo video: {video_path}")
                            return {
                                "video_path": str(video_path),
                                "duration": max_duration,
                                "text": text,
                                "background_description": background_description
                            }
                
                logger.warning("Veo API returned operation but no video found in result")
                return self._create_placeholder_video(text, background_description, max_duration)
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error generating video with Veo API: {error_msg}")
                if "not found" in error_msg.lower() or "404" in error_msg:
                    logger.warning("Veo 3.0 API not available, using placeholder")
                elif "quota" in error_msg.lower() or "429" in error_msg:
                    logger.error("Veo API quota exceeded, using placeholder")
                return self._create_placeholder_video(text, background_description, max_duration)
                
        except ImportError:
            logger.error("google.genai not installed. Run: pip install google-genai")
            return self._create_placeholder_video(text, background_description, max_duration)
        except Exception as e:
            logger.error(f"Error generating video: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_placeholder_video(text, background_description, max_duration)
    
    def _try_veo_api_direct(self, text: str, background_description: str, duration: int, video_path: Path) -> Optional[Dict]:
        """Try using Vertex AI Prediction API directly for Veo."""
        try:
            from google.cloud import aiplatform
            from google.cloud.aiplatform import initializer
            
            # Initialize
            initializer.global_config.init(
                project=self.project_id,
                location="us-central1"
            )
            
            # Use Vertex AI Prediction API
            endpoint = aiplatform.Endpoint(
                endpoint_name=f"projects/{self.project_id}/locations/us-central1/endpoints/veo-3.1"
            )
            
            # Prepare request
            prompt = f"{text} with {background_description}"
            instances = [{
                "prompt": prompt,
                "duration_seconds": duration,
                "aspect_ratio": "16:9"
            }]
            
            prediction = endpoint.predict(instances=instances)
            
            # Extract video from prediction
            if prediction and prediction.predictions:
                video_data = prediction.predictions[0].get('video_bytes') or prediction.predictions[0].get('video')
                if video_data:
                    with open(video_path, 'wb') as f:
                        if isinstance(video_data, bytes):
                            f.write(video_data)
                        else:
                            import base64
                            f.write(base64.b64decode(video_data))
                    
                    logger.info(f"Successfully generated Veo video via direct API: {video_path}")
                    return {
                        "video_path": str(video_path),
                        "duration": duration,
                        "text": text,
                        "background_description": background_description
                    }
            
            logger.warning("Direct Veo API call returned no video data")
            return self._create_placeholder_video(text, background_description, duration)
                
        except Exception as e:
            logger.warning(f"Direct Veo API call failed: {e}, using placeholder")
            return self._create_placeholder_video(text, background_description, duration)
    
    def _create_placeholder_video(self, text: str, background_description: str, duration: int) -> Dict:
        """
        Create an animated intro video with dynamic effects, motion, and visual appeal.
        This creates a cinematic animated intro until Veo API is fully available.
        
        Args:
            text: Text to display on the video (centered)
            background_description: Description of the background to create
            duration: Video duration in seconds
        """
        try:
            from moviepy import TextClip, CompositeVideoClip, ColorClip
            import numpy as np
            
            output_dir = Path("outputs/generated_videos")
            output_dir.mkdir(parents=True, exist_ok=True)
            video_path = output_dir / f"intro_{hash(text + background_description) % 10000}.mp4"
            
            fps = 24
            display_text = text[:100]  # Use the provided text directly
            
            # Create animated background using VideoClip with custom frame function
            from moviepy import VideoClip
            
            def make_animated_bg(t):
                # Create a high-quality animated background based on description
                frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
                
                # Parse background description to determine style
                desc_lower = background_description.lower()
                
                # Determine color scheme based on description
                if any(word in desc_lower for word in ['dark', 'night', 'black', 'shadow']):
                    # Dark theme
                    base_r, base_g, base_b = 10, 15, 25
                    accent_r, accent_g, accent_b = 50, 60, 80
                elif any(word in desc_lower for word in ['bright', 'light', 'white', 'sun']):
                    # Light theme
                    base_r, base_g, base_b = 200, 210, 220
                    accent_r, accent_g, accent_b = 150, 160, 180
                elif any(word in desc_lower for word in ['blue', 'ocean', 'sky', 'water']):
                    # Blue theme
                    base_r, base_g, base_b = 20, 40, 80
                    accent_r, accent_g, accent_b = 40, 80, 140
                elif any(word in desc_lower for word in ['red', 'fire', 'flame', 'energy']):
                    # Red/energy theme
                    base_r, base_g, base_b = 40, 15, 20
                    accent_r, accent_g, accent_b = 180, 50, 40
                elif any(word in desc_lower for word in ['green', 'nature', 'grass', 'field']):
                    # Green theme
                    base_r, base_g, base_b = 15, 40, 20
                    accent_r, accent_g, accent_b = 40, 120, 50
                elif any(word in desc_lower for word in ['purple', 'violet', 'magenta']):
                    # Purple theme
                    base_r, base_g, base_b = 30, 15, 40
                    accent_r, accent_g, accent_b = 100, 40, 140
                else:
                    # Default: dynamic sports theme (blue to purple gradient)
                    base_r, base_g, base_b = 25, 30, 50
                    accent_r, accent_g, accent_b = 80, 60, 120
                
                # Animated gradient with smooth color transitions
                cycle = (t % 4) / 4.0  # 4 second color cycle
                
                # Top color (darker, animated)
                top_r = int(base_r + (accent_r - base_r) * 0.3 * np.sin(cycle * np.pi * 2))
                top_g = int(base_g + (accent_g - base_g) * 0.3 * np.sin(cycle * np.pi * 2 + np.pi/3))
                top_b = int(base_b + (accent_b - base_b) * 0.3 * np.sin(cycle * np.pi * 2 + 2*np.pi/3))
                
                # Bottom color (lighter, animated)
                bot_r = int(accent_r + (base_r - accent_r) * 0.2 * np.sin(cycle * np.pi * 2 + np.pi))
                bot_g = int(accent_g + (base_g - accent_g) * 0.2 * np.sin(cycle * np.pi * 2 + np.pi + np.pi/3))
                bot_b = int(accent_b + (base_b - accent_b) * 0.2 * np.sin(cycle * np.pi * 2 + np.pi + 2*np.pi/3))
                
                # Create smooth radial gradient from center
                center_x, center_y = 960, 540
                max_dist = np.sqrt(center_x**2 + center_y**2)
                
                for y in range(1080):
                    for x in range(1920):
                        # Distance from center
                        dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                        # Normalize distance
                        norm_dist = min(1.0, dist / max_dist)
                        
                        # Radial gradient
                        blend = norm_dist ** 0.7  # Power curve for smoother gradient
                        r = int(top_r * (1 - blend) + bot_r * blend)
                        g = int(top_g * (1 - blend) + bot_g * blend)
                        b = int(top_b * (1 - blend) + bot_b * blend)
                        
                        # Add animated light rays/streaks
                        angle = np.arctan2(y - center_y, x - center_x)
                        ray_intensity = 0.3 * np.sin(angle * 3 + t * 2) * (1 - norm_dist)
                        r = min(255, int(r + ray_intensity * 30))
                        g = min(255, int(g + ray_intensity * 30))
                        b = min(255, int(b + ray_intensity * 30))
                        
                        frame[y, x] = [r, g, b]
                
                # Add animated particles/glow effects
                num_particles = 5
                for i in range(num_particles):
                    particle_angle = (t * 0.5 + i * 2 * np.pi / num_particles) % (2 * np.pi)
                    particle_dist = 200 + 150 * np.sin(t * 0.8 + i)
                    particle_x = int(center_x + particle_dist * np.cos(particle_angle))
                    particle_y = int(center_y + particle_dist * np.sin(particle_angle))
                    
                    if 0 <= particle_y < 1080 and 0 <= particle_x < 1920:
                        # Add glow effect
                        glow_size = 40
                        for dy in range(-glow_size, glow_size, 2):
                            for dx in range(-glow_size, glow_size, 2):
                                y, x = particle_y + dy, particle_x + dx
                                if 0 <= y < 1080 and 0 <= x < 1920:
                                    dist = np.sqrt(dx*dx + dy*dy)
                                    if dist < glow_size:
                                        intensity = max(0, (1 - dist/glow_size) ** 2)
                                        glow_r = min(255, int(frame[y, x, 0] + intensity * 60))
                                        glow_g = min(255, int(frame[y, x, 1] + intensity * 60))
                                        glow_b = min(255, int(frame[y, x, 2] + intensity * 60))
                                        frame[y, x] = [glow_r, glow_g, glow_b]
                
                return frame
            
            # Create animated background clip using VideoClip
            animated_bg = VideoClip(make_animated_bg, duration=duration)
            animated_bg.fps = fps
            
            # Create animated text with zoom, fade, and motion effects
            try:
                def animate_text_frame(get_frame, t):
                    frame = get_frame(t)
                    h, w = frame.shape[:2]
                    
                    # Fade in (first 0.8 seconds)
                    if t < 0.8:
                        opacity = min(1.0, t / 0.8)
                    # Fade out (last 0.8 seconds)
                    elif t > duration - 0.8:
                        opacity = (duration - t) / 0.8
                    else:
                        opacity = 1.0
                    
                    # Scale animation - zoom in then slight zoom out
                    if t < 1.2:
                        # Zoom in from 0.7 to 1.1
                        scale = 0.7 + 0.4 * (t / 1.2)
                    elif t < 2.0:
                        # Slight zoom out to 1.0
                        scale = 1.1 - 0.1 * ((t - 1.2) / 0.8)
                    else:
                        scale = 1.0
                    
                    # Horizontal motion (subtle slide)
                    x_offset = int(20 * np.sin(t * 0.5))
                    y_offset = int(10 * np.cos(t * 0.3))
                    
                    # Apply scale
                    new_h, new_w = int(h * scale), int(w * scale)
                    if new_h > 0 and new_w > 0:
                        from PIL import Image
                        pil_img = Image.fromarray(frame)
                        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
                        scaled_frame = np.array(pil_img)
                        
                        # Create new frame with offset
                        new_frame = np.zeros((h, w, 3), dtype=np.uint8)
                        y_start = max(0, (h - new_h) // 2 + y_offset)
                        x_start = max(0, (w - new_w) // 2 + x_offset)
                        y_end = min(h, y_start + new_h)
                        x_end = min(w, x_start + new_w)
                        
                        src_y_start = max(0, -((h - new_h) // 2 + y_offset))
                        src_x_start = max(0, -((w - new_w) // 2 + x_offset))
                        
                        if y_end > y_start and x_end > x_start:
                            new_frame[y_start:y_end, x_start:x_end] = scaled_frame[
                                src_y_start:src_y_start+(y_end-y_start),
                                src_x_start:src_x_start+(x_end-x_start)
                            ]
                        frame = new_frame
                    
                    # Apply opacity
                    frame = (frame * opacity).astype(np.uint8)
                    return frame
                
                # Create text clip - perfectly centered
                txt_clip = TextClip(
                    text=display_text,
                    font_size=90,
                    color='white',
                    text_align='center',
                    duration=duration,
                    size=(1800, None),
                    method='caption'
                ).with_position(('center', 'center'))  # Perfect center alignment
                
                # Apply animation using VideoClip wrapper
                from moviepy import VideoClip as VC
                def make_animated_text(t):
                    # Get base text frame at this time
                    base_frame = txt_clip.get_frame(t)
                    h, w = base_frame.shape[:2]
                    
                    # Fade in (first 0.8 seconds)
                    if t < 0.8:
                        opacity = min(1.0, t / 0.8)
                    # Fade out (last 0.8 seconds)
                    elif t > duration - 0.8:
                        opacity = (duration - t) / 0.8
                    else:
                        opacity = 1.0
                    
                    # Scale animation - zoom in then slight zoom out
                    if t < 1.2:
                        scale = 0.7 + 0.4 * (t / 1.2)
                    elif t < 2.0:
                        scale = 1.1 - 0.1 * ((t - 1.2) / 0.8)
                    else:
                        scale = 1.0
                    
                    # Horizontal motion (subtle slide)
                    x_offset = int(20 * np.sin(t * 0.5))
                    y_offset = int(10 * np.cos(t * 0.3))
                    
                    # Apply scale
                    new_h, new_w = int(h * scale), int(w * scale)
                    if new_h > 0 and new_w > 0:
                        from PIL import Image
                        pil_img = Image.fromarray(base_frame)
                        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
                        scaled_frame = np.array(pil_img)
                        
                        # Create new frame with offset
                        new_frame = np.zeros((h, w, 3), dtype=np.uint8)
                        y_start = max(0, (h - new_h) // 2 + y_offset)
                        x_start = max(0, (w - new_w) // 2 + x_offset)
                        y_end = min(h, y_start + new_h)
                        x_end = min(w, x_start + new_w)
                        
                        src_y_start = max(0, -((h - new_h) // 2 + y_offset))
                        src_x_start = max(0, -((w - new_w) // 2 + x_offset))
                        
                        if y_end > y_start and x_end > x_start:
                            new_frame[y_start:y_end, x_start:x_end] = scaled_frame[
                                src_y_start:src_y_start+(y_end-y_start),
                                src_x_start:src_x_start+(x_end-x_start)
                            ]
                        base_frame = new_frame
                    
                    # Apply opacity
                    frame = (base_frame * opacity).astype(np.uint8)
                    return frame
                
                animated_text = VC(make_animated_text, duration=duration)
                animated_text.fps = fps
                
                # Composite animated background and text
                video = CompositeVideoClip([animated_bg, animated_text])
                
            except Exception as e:
                logger.warning(f"Advanced animation failed: {e}, using simpler animation")
                # Simpler fallback: animated background with basic text
                txt_clip = TextClip(
                    text=display_text,
                    font_size=90,
                    color='white',
                    text_align='center',
                    duration=duration,
                    size=(1800, None),
                    method='caption'
                ).with_position(('center', 'center'))  # Perfect center alignment
                video = CompositeVideoClip([animated_bg, txt_clip])
            
            # Write video
            video.write_videofile(
                str(video_path),
                fps=fps,
                codec='libx264',
                audio_codec='aac',
                logger=None
            )
            
            # Cleanup
            try:
                video.close()
                animated_bg.close()
                if 'animated_text' in locals():
                    animated_text.close()
                if 'txt_clip' in locals():
                    txt_clip.close()
            except:
                pass
            
            logger.info(f"Created animated intro video: {video_path}")
            return {
                "video_path": str(video_path),
                "duration": duration,
                "text": text,
                "background_description": background_description,
                "is_placeholder": True
            }
                
        except Exception as e:
            logger.error(f"Failed to create animated video: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None


def generate_intro_video(text: str, background_description: str, max_duration: int = 5, logo_path: Optional[str] = None) -> Optional[Dict]:
    """
    Generate an intro video from text and background description.
    
    Args:
        text: Text to display on the video (centered)
        background_description: Description of the background to generate/create
        max_duration: Maximum duration in seconds
        logo_path: Optional logo to overlay
        
    Returns:
        Dict with video data or None if failed
    """
    generator = VeoGenerator()
    return generator.generate_intro_video(text, background_description, max_duration, logo_path)

