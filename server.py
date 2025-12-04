import json
from functools import partial

import trio
import asyncclick as click
from trio_websocket import ConnectionClosed, serve_websocket

TICK = 0.1

buses = {}


async def echo_server(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            decoded_message = json.loads(message)
            # print(decoded_message)
            buses[decoded_message["busId"]] = decoded_message
            # await trio.sleep(TICK)
            # await ws.send_message(message)
        except ConnectionClosed:
            break


async def talk_to_browser(request):
    ws = await request.accept()
    while True:
        try:
            message = {"msgType": "Buses", "buses": list(buses.values())}
            await ws.send_message(json.dumps(message))
            await trio.sleep(TICK)
            # message = await ws.get_message()
        except ConnectionClosed:
            break


async def main():
    serve_websocket_ssl = partial(serve_websocket, ssl_context=None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket_ssl, echo_server, "127.0.0.1", 8080)
        nursery.start_soon(serve_websocket_ssl, talk_to_browser, "127.0.0.1", 8000)


if __name__ == "__main__":
    trio.run(main)
