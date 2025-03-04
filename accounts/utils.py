import requests
import os
import logging

logger = logging.getLogger(__name__)

def transform_avatar_api(input_path):
    """
    Calls an external API (e.g., DeepAI Toonify API) to transform the image.
    Returns the URL of the transformed (cartoonized) image.
    """
    api_url = "https://api.deepai.org/api/toonify"
    api_key = "1c3abbfd-15ba-4ccb-8c80-7dbcd0f5dbac"  # Ensure this key is valid and you have credits.
    try:
        with open(input_path, 'rb') as image_file:
            response = requests.post(
                api_url,
                files={'image': image_file},
                headers={'api-key': api_key}
            )
        result = response.json()
        logger.info("DeepAI API response: %s", result)
        print("DeepAI API response:", result)  # For debugging in the console
        return result.get("output_url")
    except Exception as e:
        logger.error("Error calling DeepAI API: %s", e)
        print("Error calling DeepAI API:", e)
        return None

def download_image(image_url, output_path):
    """
    Downloads an image from image_url and saves it to output_path.
    Returns True on success, otherwise False.
    """
    try:
        response = requests.get(image_url)
        logger.info("Downloading image, status code: %s", response.status_code)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            logger.info("Image downloaded to: %s", output_path)
            return True
        else:
            logger.error("Failed to download image from URL: %s", image_url)
            return False
    except Exception as e:
        logger.error("Error downloading image: %s", e)
        return False
