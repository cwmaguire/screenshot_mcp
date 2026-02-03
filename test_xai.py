import asyncio
import os
from dotenv import load_dotenv
from xai_sdk import AsyncClient
from xai_sdk.chat import user, system, image

load_dotenv()

async def test_xai():
    client = AsyncClient(api_key=os.getenv("XAI_API_KEY"))
    chat = client.chat.create(model="grok-4")
    chat.append(system("You are Grok, a helpful AI assistant."))
    chat.append(user("Describe this image.", image("https://science.nasa.gov/wp-content/uploads/2023/09/web-first-images-release.png")))
    response = await chat.sample()
    print("Response:", response.content)

if __name__ == "__main__":
    asyncio.run(test_xai())