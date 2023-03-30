import asyncio

import yaml

from src.vacuum.command import get_status, goto, charge
from src.vacuum.protocol import Vacuum


def get_config():
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file.read())


async def main():

    config = get_config()

    robot = Vacuum(
        token=config.get('vacuum').get('token'),
        ip=config.get('vacuum').get('ip'),
        device_id=config.get('vacuum').get('id'),
        debug=config.get('debug'),
        start_id=1,
    )
    # aa = await goto(robot, [23644, 26282])
    # print(aa)

    # aa = await charge(robot)
    aa = await get_status(robot)
    # print(aa)

    # await goto(robot, [23644, 26282])
    # await get_status(robot)
    # aa = await robot.send_command('get_status')
    # aa = robot.send('get_room_mapping')
    # aa = await robot.send_command('get_consumable')
    # aa = await robot.send_command('app_segment_clean', [{'segments': [18], 'clean_order_mode': 0, 'repeat': 3}])
    # aa = robot.send('stop_segment_clean')
    # aa = robot.send('app_charge')


if __name__ == '__main__':
    asyncio.run(main())
