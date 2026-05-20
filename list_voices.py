import asyncio
from edge_tts import VoicesManager

async def run():
    voices = await VoicesManager.create()
    hi_voices = voices.find(Locale='hi-IN')
    for v in hi_voices:
        print(v['ShortName'])

if __name__ == '__main__':
    asyncio.run(run())