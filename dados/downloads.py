import json
import os
import time
import random
import requests
from PIL import Image, ImageOps
from io import BytesIO

# Import using the updated package name, falling back if necessary
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

# Configuration
JSON_FILE = "data.json"
OUTPUT_DIR = r"C:\Users\Aluno\Desktop\localMarket\public"
TARGET_SIZE = (300, 300)
LIMIT = 120

def setup_directory(path):
    """Creates the output directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

def search_image_with_retry(name, retries=3, base_backoff=5):
    """Searches for an image with retries and exponential backoff to handle 403 Rate Limits."""
    for attempt in range(retries):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.images(name, max_results=1))
                if not results:
                    return None
                return results[0]['image']
        except Exception as e:
            error_str = str(e)
            # Check if it's a rate limit or a 403 block
            if "403" in error_str or "Ratelimit" in error_str:
                sleep_time = base_backoff * (2 ** attempt) + random.uniform(1, 3)
                print(f"[!] Hit DuckDuckGo rate limit for '{name}'. Sleeping {sleep_time:.1f}s before retry...")
                time.sleep(sleep_time)
            else:
                print(f"[-] Search error for '{name}': {e}")
                return None
                
    print(f"[-] Failed to fetch image for '{name}' after {retries} attempts due to rate limits.")
    return None

def download_and_crop_image(name, filename):
    """Searches, downloads, crops, and saves the image."""
    try:
        # Search for the image URL using the robust retry function
        image_url = search_image_with_retry(name)
        if not image_url:
            print(f"[-] Skipping {name} due to missing image URL.")
            return

        # Download the image
        print(f"[*] Downloading {name}...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(image_url, headers=headers, timeout=15)
        response.raise_for_status()

        # Open image from memory
        img = Image.open(BytesIO(response.content))
        
        # Convert to RGB (handles RGBA/PNGs with transparency correctly for JPEG saving)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Crop and resize to exactly 300x300, centering the image
        img_cropped = ImageOps.fit(img, TARGET_SIZE, method=Image.Resampling.LANCZOS)

        # Build final save path
        save_path = os.path.join(OUTPUT_DIR, filename)
        
        # Save the image
        img_cropped.save(save_path, "JPEG")
        print(f"[+] Successfully saved {name} to {filename}")

    except Exception as e:
        print(f"[-] Error processing {name}: {e}")

def main():
    setup_directory(OUTPUT_DIR)

    # Load JSON data
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find {JSON_FILE}. Make sure it is in the same folder as this script.")
        return

    # Process only the first 20 entries
    for index, item in enumerate(data[:LIMIT]):
        name = item.get("desc")
        raw_image_path = item.get("imagem")
        
        if not name or not raw_image_path:
            continue
            
        # Extract just the filename (e.g., "michael_jordan.jpg")
        filename = os.path.basename(raw_image_path)
        
        # Execute download and cropping
        download_and_crop_image(name, filename)
        
        # Add a polite, randomized delay between entities to fly under the radar
        if index < LIMIT - 1:
            delay = random.uniform(2.5, 4.5)
            print(f"[*] {index} Waiting {delay:.1f} seconds before the next search...")
            time.sleep(delay)

if __name__ == "__main__":
    main()