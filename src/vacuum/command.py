from typing import Any

from src.vacuum.protocol import Vacuum


async def get_status(vacuum: Vacuum) -> dict[str, Any]:
    return await vacuum.send_command('get_status')


async def goto(vacuum: Vacuum, coordinates: list[int]) -> dict[str, Any]:
    return await vacuum.send_command('app_goto_target', coordinates)


async def charge(vacuum: Vacuum) -> dict[str, Any]:
    return await vacuum.send_command('app_charge')

