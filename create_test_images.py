"""
Create test images for testing the image posting functionality
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_test_image(text, filename, color):
    """Create a simple test image with text"""
    # Create image
    img = Image.new('RGB', (800, 600), color=color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a basic font, fallback to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except:
        font = ImageFont.load_default()
    
    # Add text to image
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    position = ((800 - text_width) // 2, (600 - text_height) // 2)
    draw.text(position, text, fill='white', font=font)
    
    # Add border
    draw.rectangle([0, 0, 799, 599], outline='black', width=5)
    
    # Save image
    img.save(filename)
    print(f"Created: {filename}")

def main():
    # Create uploads directory structure
    base_dir = "uploads/image-packs/generic"
    os.makedirs(base_dir, exist_ok=True)
    
    # Create test images matching the database entries
    test_images = [
        {
            "text": "Test Ring CAD\n(Sample Image)",
            "filename": "test_ring_cad.jpg",
            "color": (70, 130, 180)  # Steel blue
        },
        {
            "text": "Solitaire Diamond\n(Test Image)",
            "filename": "solitaire_diamond.jpg", 
            "color": (138, 43, 226)  # Blue violet
        },
        {
            "text": "Vintage Halo\n(Test Image)",
            "filename": "vintage_halo.jpg",
            "color": (165, 42, 42)  # Brown
        },
        {
            "text": "Three Stone Ring\n(Test Image)",
            "filename": "three_stone.jpg",
            "color": (60, 179, 113)  # Medium sea green
        },
        {
            "text": "Diamond Studs\n(Test Image)",
            "filename": "diamond_studs.jpg",
            "color": (255, 140, 0)  # Dark orange
        },
        {
            "text": "Pearl Drops\n(Test Image)",
            "filename": "pearl_drops.jpg",
            "color": (199, 21, 133)  # Medium violet red
        }
    ]
    
    for img_config in test_images:
        filepath = os.path.join(base_dir, img_config["filename"])
        create_test_image(
            img_config["text"],
            filepath,
            img_config["color"]
        )
    
    print(f"\nAll test images created in: {os.path.abspath(base_dir)}")
    print("\nThese images can now be used for testing the Facebook image posting feature.")
    print("The images match the filenames in your database image packs.")

if __name__ == "__main__":
    main()