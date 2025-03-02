# accounts/utils.py
import requests
import os

def transform_avatar_api(input_path):
    """
    Call an external API (e.g., DeepAI Toonify API) to transform the image.
    Returns the URL of the transformed (cartoonized) image.
    """
    api_url = "https://api.deepai.org/api/toonify"
    api_key = "YOUR_API_KEY"  # Replace with your actual API key.
    with open(input_path, 'rb') as image_file:
        response = requests.post(
            api_url,
            files={'image': image_file},
            headers={'api-key': api_key}
        )
    result = response.json()
    return result.get("output_url")  # Expected to be a URL string.

def download_image(image_url, output_path):
    """
    Downloads an image from image_url and saves it to output_path.
    Returns True on success, otherwise False.
    """
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    return False
