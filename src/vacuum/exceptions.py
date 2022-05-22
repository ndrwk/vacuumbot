class DeviceError(Exception):
    """Device error with details."""

    code: str = None
    message: str = None

    def __init__(self, error: str | dict[str, str]):
        """Error init.

        Args:
            error: device error
        """
        if isinstance(error, dict):
            self.code = error.get('code')
            self.message = error.get('message')


class PayloadDecodeError(DeviceError):
    """Exception for failures in payload decoding."""
