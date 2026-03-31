import asyncio
import os
import sys
import pyaudio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

async def main():
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    print("Initiating connection...")
    try:
        async with client.aio.live.connect(model="gemini-2.0-flash") as session:
            print("Connected!", type(session))
            # Send sample audio
            await session.send(input={"realtime_input": {"media_chunks": [{"mime_type": "audio/pcm;rate=16000", "data": b'xx'*512}]}})
            print("Successfully sent audio using dict input!")
            
            # Close session nicely
            await session.send(input=types.LiveClientContent(
                realtime_input=types.LiveClientRealtimeInput(
                    media_chunks=[types.Blob(mime_type="audio/pcm;rate=16000", data=b'xx'*512)]
                )
            ))
            print("Successfully sent audio using Object input!")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
