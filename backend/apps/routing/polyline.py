"""Google encoded polyline decoding (precision 5)."""

from __future__ import annotations

from .domain import LatLon


def decode_polyline(encoded: str, precision: int = 5) -> list[LatLon]:
    coords: list[LatLon] = []
    index = lat = lng = 0
    factor = 10**precision
    length = len(encoded)
    while index < length:
        deltas = []
        for _ in range(2):
            result = shift = 0
            while True:
                if index >= length:
                    raise ValueError("Malformed polyline")
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lng += deltas[1]
        coords.append((lat / factor, lng / factor))
    return coords
