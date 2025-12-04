import json
import logging
import os
from contextlib import suppress
from functools import wraps
from itertools import cycle, islice
from random import choice

import asyncclick as click
import trio
from trio_websocket import ConnectionClosed, HandshakeError, open_websocket_url

logger = logging.getLogger(__name__)


def relaunch_on_disconect(time):
    def real_decorator(async_func):
        @wraps(async_func)
        async def wrapper(*args, **kwargs):
            while True:
                try:
                    return await async_func(*args, **kwargs)
                except ConnectionClosed:
                    logger.error("Соединение разорвано")
                    await trio.sleep(time)
                except HandshakeError:
                    logger.error("Ошибка при установке соединения")
                    await trio.sleep(time)

        return wrapper

    return real_decorator


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


def load_routes(limit=-1, directory_path="routes"):
    for filename in os.listdir(directory_path)[:limit]:
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, "r", encoding="utf8") as file:
                yield json.load(file)


async def run_bus(send_channel, bus_id, route, bus_name, refresh_timeout):
    for location in route:
        message = {
            "busId": bus_id,
            "lat": location[0],
            "lng": location[1],
            "route": bus_name,
        }
        await send_channel.send(json.dumps(message, ensure_ascii=False))
        await trio.sleep(refresh_timeout)


@relaunch_on_disconect(5)
async def send_updates(server_address, receive_channel):
    async with open_websocket_url(server_address) as ws:
        async for value in receive_channel:
            await ws.send_message(value)
            logger.info(f"Отправлено сообщение: {value}")


@click.command()
@click.option("--server", default="ws://localhost:8080", help="Адрес сервера")
@click.option("--routes_number", default=10, help="Количество маршрутов")
@click.option("--buses_per_route", default=30, help="Количество автобусов на маршруте")
@click.option("--websocket_numbers", default=5, help="Количество websocket")
@click.option(
    "--emulator_id",
    default="em1",
    help="префикс к busId на случай запуска нескольких экземпляров имитатора",
)
@click.option(
    "--refresh_timeout", default=0.1, help="задержка в обновлении координат сервера"
)
@click.option("-v", is_flag=True, default=True, help="вывод в консоль")
async def main(
    server,
    routes_number,
    buses_per_route,
    websocket_numbers,
    emulator_id,
    refresh_timeout,
    v,
):
    if v:
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.StreamHandler())
        logger.info("Вывод в консоль включен")
    with suppress(KeyboardInterrupt):
        async with trio.open_nursery() as nursery:
            channels = [
                trio.open_memory_channel(0) for i in range(websocket_numbers)
            ]  # send, receive
            logger.debug(f"Открываем {websocket_numbers} websocket")
            for channel in channels:
                _, receive = channel
                nursery.start_soon(send_updates, server, receive)
            for bus_route in load_routes(routes_number):
                for i in range(buses_per_route):
                    send, _ = choice(channels)
                    nursery.start_soon(
                        run_bus,
                        send,
                        generate_bus_id(f"{emulator_id}-i", bus_route["name"]),
                        islice(cycle(bus_route["coordinates"]), i * 10, None),
                        bus_route["name"],
                        refresh_timeout,
                    )


if __name__ == "__main__":
    trio.run(main.main)
