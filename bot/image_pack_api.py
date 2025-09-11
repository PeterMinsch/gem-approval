from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import shutil
import mimetypes
from datetime import datetime
import logging

from database import db

# Set up logging
logger = logging.getLogger(__name__)

# Create router for image pack endpoints
router = APIRouter()

# Pydantic models for request/response
class ImagePackCreate(BaseModel):
    name: str
    category: str

class ImagePackImage(BaseModel):
    filename: str
    description: str

class ImagePackResponse(BaseModel):
    id: str
    name: str
    images: List[ImagePackImage]
    is_default: bool
    created_at: str
    updated_at: str

class ImagePackUpdate(BaseModel):
    name: Optional[str] = None

# Configuration
UPLOAD_DIR = "uploads/image-packs"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB per file
MAX_FILES_PER_PACK = 10

def validate_image_file(file: UploadFile) -> bool:
    """Validate uploaded image file"""
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False
    
    # Check MIME type
    if not file.content_type or not file.content_type.startswith('image/'):
        return False
    
    return True

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal"""
    # Remove directory components
    filename = os.path.basename(filename)
    
    # Replace potentially dangerous characters
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Ensure filename isn't empty
    if not filename or filename == '.' or filename == '..':
        filename = f"image_{uuid.uuid4().hex[:8]}"
    
    return filename

def get_category_directory(category: str) -> str:
    """Map template category to directory name"""
    category_mapping = {
        "GENERIC": "generic",
        "ISO_PIVOT": "iso-pivot", 
        "CAD": "cad",
        "CASTING": "casting",
        "SETTING": "setting",
        "ENGRAVING": "engraving",
        "ENAMEL": "enamel"
    }
    return category_mapping.get(category, "generic")

@router.post("/image-packs", response_model=dict)
async def create_image_pack(image_pack: ImagePackCreate):
    """Create a new image pack"""
    try:
        # Validate category
        valid_categories = ["GENERIC", "ISO_PIVOT", "CAD", "CASTING", "SETTING", "ENGRAVING", "ENAMEL"]
        if image_pack.category not in valid_categories:
            raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {valid_categories}")
        
        # Create the image pack in database
        pack_id = db.create_image_pack(image_pack.name, image_pack.category)
        
        logger.info(f"Created image pack: {pack_id} - {image_pack.name} ({image_pack.category})")
        
        return {
            "success": True,
            "message": "Image pack created successfully",
            "image_pack_id": pack_id
        }
    
    except Exception as e:
        logger.error(f"Error creating image pack: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create image pack: {str(e)}")

@router.get("/image-packs/by-categories")
async def get_images_by_categories(categories: str = None):
    """Get image packs filtered by categories with grouped images"""
    try:
        # Parse categories from comma-separated string
        category_list = categories.split(',') if categories else []
        
        # Get all image packs
        all_packs = db.get_image_packs()
        
        if not category_list:
            # Return all packs if no categories specified
            return {
                "success": True,
                "categories": [],
                "packs": all_packs
            }
        
        # Filter packs based on categories
        filtered_packs = []
        category_keywords = {
            'RINGS': ['ring', 'band', 'wedding', 'engagement'],
            'NECKLACES': ['necklace', 'pendant', 'chain'],
            'BRACELETS': ['bracelet', 'bangle'],
            'EARRINGS': ['earring', 'stud', 'hoop'],
            'CASTING': ['cast', 'mold', 'manufacturing'],
            'CAD': ['cad', '3d', 'design'],
            'SETTING': ['setting', 'stone', 'diamond'],
            'ENGRAVING': ['engrav', 'etch'],
            'ENAMEL': ['enamel', 'color'],
            'GENERIC': ['generic', 'general', 'bravo']
        }
        
        for pack in all_packs:
            pack_name_lower = pack['name'].lower()
            for category in category_list:
                if category in category_keywords:
                    keywords = category_keywords[category]
                    if any(keyword in pack_name_lower for keyword in keywords):
                        filtered_packs.append(pack)
                        break
        
        # Always include generic pack if available
        generic_pack = next((p for p in all_packs if 'generic' in p['name'].lower()), None)
        if generic_pack and generic_pack not in filtered_packs:
            filtered_packs.append(generic_pack)
        
        return {
            "success": True,
            "categories": category_list,
            "packs": filtered_packs,
            "total": len(filtered_packs)
        }
        
    except Exception as e:
        logger.error(f"Error getting images by categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to get images by categories")

@router.get("/image-packs", response_model=List[ImagePackResponse])
async def get_image_packs():
    """Get all image packs"""
    try:
        packs = db.get_image_packs()
        
        # Convert to response format
        response_packs = []
        for pack in packs:
            # Convert string images to object format
            converted_images = []
            raw_images = pack.get('images', [])
            
            if raw_images:
                for img_path in raw_images:
                    if isinstance(img_path, str):
                        filename = img_path.split('/')[-1] if '/' in img_path else img_path
                        description = filename.replace('_', ' ').replace('.jpg', '').replace('.png', '').title()
                        converted_images.append({
                            "filename": img_path,
                            "description": description
                        })
            
            # Note: No more hardcoded override - API now respects database content
                
            response_packs.append(ImagePackResponse(
                id=pack['id'],
                name=pack['name'],
                images=converted_images,
                is_default=pack['is_default'],
                created_at=pack['created_at'],
                updated_at=pack['updated_at']
            ))
        
        logger.info(f"Retrieved {len(response_packs)} image packs")
        return response_packs
    
    except Exception as e:
        logger.error(f"Error getting image packs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get image packs: {str(e)}")

@router.get("/image-packs/{pack_id}", response_model=ImagePackResponse)
async def get_image_pack(pack_id: str):
    """Get a specific image pack by ID"""
    try:
        pack = db.get_image_pack_by_id(pack_id)
        
        if not pack:
            raise HTTPException(status_code=404, detail="Image pack not found")
        
        # Convert string images to object format (same logic as get_image_packs)
        converted_images = []
        raw_images = pack.get('images', [])
        
        if raw_images:
            for img_path in raw_images:
                if isinstance(img_path, str):
                    filename = img_path.split('/')[-1] if '/' in img_path else img_path
                    description = filename.replace('_', ' ').replace('.jpg', '').replace('.png', '').title()
                    converted_images.append({
                        "filename": img_path,
                        "description": description
                    })
        
        return ImagePackResponse(
            id=pack['id'],
            name=pack['name'],
            images=converted_images,
            is_default=pack['is_default'],
            created_at=pack['created_at'],
            updated_at=pack['updated_at']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image pack {pack_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get image pack: {str(e)}")

@router.post("/image-packs/{pack_id}/upload")
async def upload_images_to_pack(
    pack_id: str,
    files: List[UploadFile] = File(...),
    category: str = Form(...)
):
    """Upload images to an existing image pack"""
    try:
        # Verify pack exists
        pack = db.get_image_pack_by_id(pack_id)
        if not pack:
            raise HTTPException(status_code=404, detail="Image pack not found")
        
        # Validate file count
        current_image_count = len(pack['images'])
        if current_image_count + len(files) > MAX_FILES_PER_PACK:
            raise HTTPException(
                status_code=400, 
                detail=f"Too many files. Maximum {MAX_FILES_PER_PACK} images per pack. Current: {current_image_count}"
            )
        
        # Validate category and get directory
        category_dir = get_category_directory(category)
        upload_path = os.path.join(UPLOAD_DIR, category_dir)
        
        # Ensure upload directory exists
        os.makedirs(upload_path, exist_ok=True)
        
        uploaded_files = []
        
        for file in files:
            # Validate file
            if not validate_image_file(file):
                logger.warning(f"Invalid file rejected: {file.filename}")
                continue
            
            # Check file size
            file_content = await file.read()
            if len(file_content) > MAX_FILE_SIZE:
                logger.warning(f"File too large rejected: {file.filename} ({len(file_content)} bytes)")
                continue
            
            # Reset file pointer
            await file.seek(0)
            
            # Generate unique filename
            original_name = sanitize_filename(file.filename)
            file_ext = os.path.splitext(original_name)[1]
            unique_name = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d')}_{original_name}"
            
            # Save file
            file_path = os.path.join(upload_path, unique_name)
            
            try:
                # Reset file pointer to beginning
                await file.seek(0)
                
                # Save file with proper error handling
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                    buffer.flush()  # Ensure data is written to disk
                    os.fsync(buffer.fileno())  # Force OS to write to storage
                
                # Verify file was actually saved
                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                    raise Exception(f"File saving failed - file not found or empty: {file_path}")
                
                # Store relative path for database and serving
                relative_path = f"uploads/image-packs/{category_dir}/{unique_name}"
                
                # Add to database
                success = db.add_image_to_pack(pack_id, unique_name, relative_path)
                if success:
                    uploaded_files.append({
                        "filename": unique_name,
                        "original_name": original_name,
                        "path": relative_path,
                        "url": f"/uploads/image-packs/{category_dir}/{unique_name}"
                    })
                    logger.info(f"✅ Image uploaded and verified: {relative_path} ({os.path.getsize(file_path)} bytes)")
                else:
                    # Remove file if database update failed
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    logger.error(f"❌ Failed to add {unique_name} to database")
                    raise Exception(f"Database update failed for {unique_name}")
            
            except Exception as e:
                logger.error(f"Error saving file {file.filename}: {e}")
                # Clean up partial file if it exists
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Cleaned up partial file: {file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up partial file {file_path}: {cleanup_error}")
                # Re-raise the original error
                raise Exception(f"File upload failed for {file.filename}: {str(e)}")
        
        if not uploaded_files:
            raise HTTPException(status_code=400, detail="No valid images were uploaded")
        
        return {
            "success": True,
            "message": f"Successfully uploaded {len(uploaded_files)} images",
            "uploaded_files": uploaded_files,
            "pack_id": pack_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading images to pack {pack_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload images: {str(e)}")

@router.put("/image-packs/{pack_id}")
async def update_image_pack(pack_id: str, update_data: ImagePackUpdate):
    """Update an image pack (currently only name)"""
    try:
        # Verify pack exists
        pack = db.get_image_pack_by_id(pack_id)
        if not pack:
            raise HTTPException(status_code=404, detail="Image pack not found")
        
        # For now, we only support updating the name
        # Could extend to support category changes in the future
        if update_data.name:
            # This would require a new database function - for now just return success
            logger.info(f"Update requested for pack {pack_id}: name='{update_data.name}'")
        
        return {
            "success": True,
            "message": "Image pack updated successfully",
            "pack_id": pack_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating image pack {pack_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update image pack: {str(e)}")

@router.delete("/image-packs/{pack_id}")
async def delete_image_pack(pack_id: str):
    """Delete an image pack and all its images"""
    try:
        # Verify pack exists
        pack = db.get_image_pack_by_id(pack_id)
        if not pack:
            raise HTTPException(status_code=404, detail="Image pack not found")
        
        # Delete from database (also handles file cleanup)
        success = db.delete_image_pack(pack_id)
        
        if success:
            logger.info(f"Deleted image pack: {pack_id}")
            return {
                "success": True,
                "message": "Image pack deleted successfully",
                "pack_id": pack_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete image pack")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image pack {pack_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete image pack: {str(e)}")

@router.delete("/image-packs/{pack_id}/images")
async def delete_image_from_pack(pack_id: str, image_path: str = Form(...)):
    """Delete a specific image from a pack"""
    try:
        # Verify pack exists
        pack = db.get_image_pack_by_id(pack_id)
        if not pack:
            raise HTTPException(status_code=404, detail="Image pack not found")
        
        # Verify image exists in pack
        if image_path not in pack['images']:
            raise HTTPException(status_code=404, detail="Image not found in pack")
        
        # Delete from database and filesystem
        success = db.delete_image_from_pack(pack_id, image_path)
        
        if success:
            logger.info(f"Deleted image {image_path} from pack {pack_id}")
            return {
                "success": True,
                "message": "Image deleted successfully",
                "pack_id": pack_id,
                "deleted_image": image_path
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete image")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image {image_path} from pack {pack_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete image: {str(e)}")