from google import genai
import os

# --- CONTENT GENERATION ---

def generate_text_content(client: genai.Client, prompt: str) -> str:
    """Uses Gemini 2.5 Flash to generate personalized text content (poem or story)."""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=None
        )
        return response.text
    except Exception as e:
        return f"ERROR: Failed to generate content due to API issue: {e}"

# Placeholder function for future image generation (Gift 3)
def generate_image_content(client: genai.Client, prompt: str) -> str:
    """
    Placeholder for image generation. Returns a high-quality placeholder image
    since full image generation requires more complex configuration for free tier.
    """
    encoded_text = prompt.replace(" ", "%20")
    placeholder_url = f"https://placehold.co/400x300/e91e63/ffffff?text=Anushka%27s%20Illustration%20({encoded_text[:20]}...)"
    
    return f"<img src='{placeholder_url}' alt='Personalized Illustration' style='max-width: 100%; border-radius: 10px; margin-top: 15px; border: 3px solid #e91e63;'>"