import asyncio
import time

async def get_data(name, seconds):
    print(f"Starting {name}")
    await asyncio.sleep(seconds)
    print(f"Finished {name}")

async def main():
    start = time.perf_counter()
    await asyncio.gather(
        get_data("Environmental", 3),
        get_data("Research", 5),
        get_data("Geospatial", 2)
    )
    end = time.perf_counter()
    print(f"Total time: {end - start:.2f} seconds")

asyncio.run(main())