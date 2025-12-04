import json
from functools import partial

import trio
import asyncclick as click
from trio_websocket import ConnectionClosed, serve_websocket
import logging

TICK = 1

buses = {}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
logger.addHandler


async def listen_browser(ws):
    while True:
        try:
            message = await ws.get_message()
            decoded_message = json.loads(message)
            logger.debug(f"Получены координаты от браузера: {decoded_message}")

        except ConnectionClosed:
            break


async def listen_buses(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            decoded_message = json.loads(message)
            buses[decoded_message["busId"]] = decoded_message
            logger.info(f"Получены координаты от автобуса: {decoded_message}")
        except ConnectionClosed:
            break


async def send_to_browser(ws):
    while True:
        try:
            message = {"msgType": "Buses", "buses": list(buses.values())}
            await ws.send_message(json.dumps(message))
            logger.info(f"Отправлены координаты автобусов: {message}")
            await trio.sleep(TICK)
        except ConnectionClosed:
            break


async def talk_to_browser(request):
    ws = await request.accept()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws)
        nursery.start_soon(send_to_browser, ws)


async def main():
    serve_websocket_ssl = partial(serve_websocket, ssl_context=None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket_ssl, listen_buses, "127.0.0.1", 8080)
        nursery.start_soon(serve_websocket_ssl, talk_to_browser, "127.0.0.1", 8000)


if __name__ == "__main__":
    trio.run(main)
