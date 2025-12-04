from pydantic import BaseModel
from dataclasses import dataclass


class Bus(BaseModel):
    busId: str
    lat: float
    lng: float
    route: str


class Bounds(BaseModel):
    south_lat: float
    north_lat: float
    west_lng: float
    east_lng: float


class BoundsMessage(BaseModel):
    msgType: str = "newBounds"
    data: Bounds


class MessageToBrowser(BaseModel):
    msgType: str = "Buses"
    buses: list[Bus]


@dataclass
class Window:
    south_lat: float = 0
    north_lat: float = 0
    west_lng: float = 0
    east_lng: float = 0

    def is_inside(self, bus: Bus) -> bool:
        return (
            self.south_lat <= bus.lat <= self.north_lat
            and self.west_lng <= bus.lng <= self.east_lng
        )

    def update(self, bounds: Bounds):
        self.south_lat = bounds.south_lat
        self.north_lat = bounds.north_lat
        self.west_lng = bounds.west_lng
        self.east_lng = bounds.east_lng
