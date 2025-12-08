import logging
from contextlib import suppress
from functools import partial

import asyncclick as click
import trio
from trio_websocket import (
    ConnectionClosed,
    WebSocketConnection,
    WebSocketRequest,
    serve_websocket,
)

from models import BoundsMessage, Bus, MessageToBrowser, Window

buses: dict[str, Bus] = {}

logger = logging.getLogger(__name__)


async def listen_browser(ws, window: Window):
    while True:
        try:
            message = await ws.get_message()
            bounds = BoundsMessage.model_validate_json(message)
            logger.debug(f"Получены координаты от браузера: {bounds}")
            window.update(bounds.data)
        except ConnectionClosed:
            break


async def listen_buses(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            bus = Bus.model_validate_json(message)
            buses[bus.busId] = Bus.model_validate_json(message)
            logger.debug(f"Получены координаты от автобуса: {bus}")
        except ConnectionClosed:
            break


def filter_buses(window: Window):
    return [bus for bus in buses.values() if window.is_inside(bus)]


async def send_buses(ws: WebSocketConnection, window: Window):
    while True:
        try:
            message = MessageToBrowser(buses=filter_buses(window))
            await ws.send_message(message.model_dump_json())
            logger.debug(f"Отправлены координаты автобусов: {message}")
        except ConnectionClosed:
            break


async def talk_to_browser(request: WebSocketRequest):
    ws = await request.accept()
    window = Window()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws, window)
        nursery.start_soon(send_buses, ws, window)


@click.command()
@click.option("--bus_port", default=8080, help="Адрес сервера")
@click.option("--browser_port", default=8000, help="Количество маршрутов")
@click.option("-v", is_flag=True, default=True, help="вывод в консоль")
async def main(bus_port, browser_port, v):
    if v:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        logger.info("Вывод в консоль включен")
    serve_websocket_ssl = partial(serve_websocket, ssl_context=None)
    with suppress(KeyboardInterrupt):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(serve_websocket_ssl, listen_buses, "127.0.0.1", bus_port)
            nursery.start_soon(
                serve_websocket_ssl, talk_to_browser, "127.0.0.1", browser_port
            )


if __name__ == "__main__":
    trio.run(main.main)
