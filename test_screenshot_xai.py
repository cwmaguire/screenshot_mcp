import base64
import asyncio
import os
from dotenv import load_dotenv
from xai_sdk import AsyncClient
from xai_sdk.chat import user, system, image
from PIL import Image
import io

load_dotenv()

async def test_screenshot():
    # Load the screenshot
    img = Image.open("/tmp/test_screenshot.png")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    client = AsyncClient(api_key=os.getenv("XAI_API_KEY"))
    chat = client.chat.create(model="grok-4")
    chat.append(system("You are Grok, a helpful AI assistant."))
    chat.append(user("Provide a detailed debugging description of this image.", image(f"data:image/png;base64,{img_base64}")))
    response = await chat.sample()
    print("Grok-4 description:")
    print(response.content)

if __name__ == "__main__":
    asyncio.run(test_screenshot())