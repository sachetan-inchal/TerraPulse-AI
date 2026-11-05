import asyncio

async def get_data():
    print("Starting data retrieval")
    await asyncio.sleep(3)
    print("Data retrieved")
    return "Air quality data"

async def main():
    result = await get_data()
    print(result)

asyncio.run(main())