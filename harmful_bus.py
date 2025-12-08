import trio

from trio_websocket import open_websocket_url


async def main():
    async with open_websocket_url("ws://127.0.0.1:8080") as ws:
        await ws.send_message('{}')
        await ws.send_message('{a:5}')
        while True:
            message = await ws.get_message()
            print(f"Response: {message}")

if __name__ == "__main__":
    trio.run(main)
