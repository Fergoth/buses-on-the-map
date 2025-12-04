import json
import os
from itertools import cycle, islice
from random import choice
from sys import stderr

import asyncclick as click
import trio
from trio_websocket import open_websocket_url

import logging


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


async def send_updates(server_address, receive_channel):
    async with open_websocket_url(server_address) as ws:
        async for value in receive_channel:
            await ws.send_message(value)


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
@click.option("-v", is_flag=True, help="вывод в консоль")
async def main(
    server,
    routes_number,
    buses_per_route,
    websocket_numbers,
    emulator_id,
    refresh_timeout,
    v, 
):
    print(f"{server} {routes_number} {buses_per_route} {websocket_numbers} {emulator_id} {refresh_timeout}")
    try:
        async with trio.open_nursery() as nursery:
            channels = [
                trio.open_memory_channel(0) for i in range(websocket_numbers)
            ]  # send, receive
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
                        refresh_timeout
                    )
    except OSError as ose:
        print("Connection attempt failed: %s" % ose, file=stderr)


if __name__ == "__main__":
    trio.run(main)
