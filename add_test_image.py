#!/usr/bin/env python3
"""
Test script to add an image to an image pack
"""

import requests
import sys
import os

# API endpoint
base_url = "http://localhost:8000"

def add_image_to_pack(pack_id, image_path):
    """Add an image to an existing image pack"""
    
    # Check if file exists
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return False
    
    # Prepare the file for upload
    with open(image_path, 'rb') as f:
        files = {'file': (os.path.basename(image_path), f, 'image/png')}
        
        # Send POST request
        response = requests.post(
            f"{base_url}/api/image-packs/{pack_id}/images",
            files=files
        )
    
    if response.status_code == 200:
        print(f"Success! Image added to pack {pack_id}")
        print(f"Response: {response.json()}")
        return True
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def create_new_pack(name, category="GENERIC"):
    """Create a new image pack"""
    response = requests.post(
        f"{base_url}/api/image-packs",
        params={"name": name, "category": category}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Created new pack: {name} (ID: {result['id']})")
        return result['id']
    else:
        print(f"Error creating pack: {response.status_code}")
        print(f"Response: {response.text}")
        return None

if __name__ == "__main__":
    # Create a new pack for jewelry images
    pack_name = "Jewelry Showcase"
    print(f"Creating new image pack: {pack_name}")
    
    new_pack_id = create_new_pack(pack_name, "JEWELRY")
    
    if new_pack_id:
        print(f"\nNew pack created with ID: {new_pack_id}")
        print("\nTo add the ring image you showed me:")
        print("1. Save your ring image as 'ring.png' in the bot directory")
        print(f"2. Run: python add_test_image.py {new_pack_id} ring.png")
    
    # If command line arguments provided, use them
    if len(sys.argv) == 3:
        pack_id = sys.argv[1]
        image_path = sys.argv[2]
        print(f"\nAdding {image_path} to pack {pack_id}...")
        add_image_to_pack(pack_id, image_path)