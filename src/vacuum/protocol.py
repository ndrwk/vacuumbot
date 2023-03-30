import asyncio
import json
import sys
from datetime import datetime
from typing import Any

from loguru import logger

from src.vacuum.exceptions import DeviceError
from src.vacuum.message import Message


class UDPSocket(asyncio.DatagramProtocol):
    """UDP protocol."""

    def __init__(self, request: bytes, response: asyncio.Future) -> None:
        """Init the UDP protocol.

        Args:
            request: message to send to robot
            response: result
        """
        self.request = request
        self.response = response
        self.transport = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        """Called when a connection is made.

        Args:
            transport: transport
        """
        self.transport = transport
        self.transport.sendto(self.request)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Called when some datagram is received.

        Args:
            data: data to send
            addr: address
        """
        if addr == self.transport._address:
            self.response.set_result(data)


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
        debug: bool = None,
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
        logger.add(sys.stdout, level=level)

    def __to_iso(self, value: Any) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()

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
        logger.debug(
            f'Sent to {self.ip}:{self.port}\n'
            f'{json.dumps(msg, indent=4, default=self.__to_iso)}',
        )

        event_loop = asyncio.get_running_loop()
        answer = event_loop.create_future()
        transport, _ = await event_loop.create_datagram_endpoint(
            lambda: UDPSocket(Message.build(msg, token=self.token), answer),
            remote_addr=(self.ip, self.port),
        )

        try:
            data = await asyncio.wait_for(answer, self.timeout)
        except asyncio.exceptions.TimeoutError as ex:
            if retry_count > 0:
                retry_count -= 1
                logger.debug(f'Retrying: {retry_count=}')
                self.start_id += 1
                return await self.send_command(
                    command,
                    parameters,
                    retry_count,
                    extra_parameters=extra_parameters,
                )
            logger.error('No response from the device')
            raise DeviceError('No response from the device') from ex
        finally:
            transport.close()

        message = Message.parse(data, token=self.token)
        payload = message.data.value
        logger.debug(
            'payload: \n'
            f'{json.dumps(payload, indent=4, default=self.__to_iso)}',
        )

        self.start_id = payload['id']
        self.start_id = 0 if self.start_id >= 9999 else self.start_id + 1

        if payload.get('error'):
            raise DeviceError(payload['error'])

        return payload.get('result', payload)
