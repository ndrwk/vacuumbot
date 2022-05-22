import socket
import sys
from asyncio import get_running_loop
from datetime import datetime
from typing import Any

from loguru import logger

from src.vacuum.exceptions import DeviceError
from src.vacuum.message import Message


class Vacuum:
    """Vacuum robot connection."""

    port = 54321

    def __init__(
        self,
        token: str,
        ip: str,
        device_id: int,
        start_id: int = 0,
        timeout: int = 5,
        debug: bool = False,
    ) -> None:
        """Init a device connect.

        Args:
            token: device token
            ip: device ip
            device_id: device id
            start_id: initial message id
            timeout: timeout
            debug: debug enable
        """
        self.ip = ip
        self.token = bytes.fromhex(token)
        self.timeout = timeout
        self.start_id = start_id
        self.device_id = device_id
        level = 'DEBUG' if debug else 'INFO'
        logger.remove()
        logger.add(sys.stderr, level=level)

    async def send_command(
        self,
        command: str,
        parameters: list[Any] = None,
        retry_count: int = 10,
        extra_parameters: dict[str, Any] = None,
    ) -> Any:
        """Send a command to the device.

        Args:
            command: command
            parameters: parameters
            retry_count: retry count
            extra_parameters: extra parameters

        Returns:
            result of the command

        Raises:
            DeviceError: if an error occurred
        """
        request = {
            'id': self.start_id,
            'method': command,
            'params': parameters or [],
        }
        if extra_parameters:
            request.update(extra_parameters)

        msg = {
            'data': {'value': request},
            'header': {
                'value': {
                    'length': 0,
                    'unknown': 0x00000000,
                    'device_id': self.device_id,
                    'ts': datetime.utcnow(),
                },
            },
            'checksum': 0,
        }
        logger.debug(f'{self.ip}:{self.port} >> {msg}')

        message = Message.build(msg, token=self.token)

        robot_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        robot_socket.settimeout(self.timeout)
        robot_socket.connect((self.ip, self.port))

        event_loop = get_running_loop()

        await event_loop.sock_sendall(robot_socket, message)

        try:
            data = await event_loop.sock_recv(robot_socket, 4096)
        except OSError as ex:
            if retry_count > 0:
                retry_count -= 1
                logger.debug(
                    f'Retrying: {retry_count=}',
                )
                self.start_id += 1
                return await self.send_command(
                    command,
                    parameters,
                    retry_count,
                    extra_parameters=extra_parameters,
                )
            logger.error('No response from the device')
            raise DeviceError('No response from the device') from ex

        message = Message.parse(data, token=self.token)
        payload = message.data.value
        logger.debug(f'{payload=}')

        self.start_id = payload['id']
        self.start_id = 0 if self.start_id >= 9999 else self.start_id + 1

        if payload.get('error'):
            raise DeviceError(payload['error'])

        return payload.get('result', payload)
