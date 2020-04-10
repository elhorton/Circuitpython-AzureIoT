"""Connectivity to Azure IoT Hub
"""

from iot_mqtt import IoT_MQTT
from listener import Listener
import adafruit_logging as logging


def _validate_keys(connection_string_parts):
    """Raise ValueError if incorrect combination of keys
    """
    host_name = connection_string_parts.get(HOST_NAME)
    shared_access_key_name = connection_string_parts.get(SHARED_ACCESS_KEY_NAME)
    shared_access_key = connection_string_parts.get(SHARED_ACCESS_KEY)
    device_id = connection_string_parts.get(DEVICE_ID)

    if host_name and device_id and shared_access_key:
        pass
    elif host_name and shared_access_key and shared_access_key_name:
        pass
    else:
        raise ValueError("Invalid Connection String - Incomplete")


DELIMITER = ";"
VALUE_SEPARATOR = "="

HOST_NAME = "HostName"
SHARED_ACCESS_KEY_NAME = "SharedAccessKeyName"
SHARED_ACCESS_KEY = "SharedAccessKey"
SHARED_ACCESS_SIGNATURE = "SharedAccessSignature"
DEVICE_ID = "DeviceId"
MODULE_ID = "ModuleId"
GATEWAY_HOST_NAME = "GatewayHostName"

VALID_KEYS = [
    HOST_NAME,
    SHARED_ACCESS_KEY_NAME,
    SHARED_ACCESS_KEY,
    SHARED_ACCESS_SIGNATURE,
    DEVICE_ID,
    MODULE_ID,
    GATEWAY_HOST_NAME,
]


class IoTHubDevice(Listener):
    """A device client for the Azure IoT Hub service
    """

    # pylint: disable=C0103
    DIRECT_METHOD_EVENT_NAME = "DirectMethod"
    TWIN_DESIRED_PROPERTIES_UPDATED_EVENT_NAME = "TwinDesiredPropertiesUpdated"
    CONNECTION_STATUS_EVENT_NAME = "ConnectionStatus"
    CLOUD_TO_DEVICE_MESSAGE_RECEIVED_EVENT_NAME = "CloudToDeviceMessageReceived"

    def __init__(self, device_connection_string: str, token_expires: int = 21600, logger: logging = None):
        super(IoTHubDevice, self).__init__()
        self._device_connection_string = device_connection_string
        self._token_expires = token_expires
        self._logger = logger if logger is not None else logging.getLogger("log")

        connection_string_values = {}

        try:
            cs_args = device_connection_string.split(DELIMITER)
            connection_string_values = dict(arg.split(VALUE_SEPARATOR, 1) for arg in cs_args)
        except (ValueError, AttributeError):
            raise ValueError("Connection string is required and should not be empty or blank and must be supplied as a string")

        if len(cs_args) != len(connection_string_values):
            raise ValueError("Invalid Connection String - Unable to parse")

        _validate_keys(connection_string_values)

        self._hostname = connection_string_values[HOST_NAME]
        self._device_id = connection_string_values[DEVICE_ID]
        self._shared_access_key = connection_string_values[SHARED_ACCESS_KEY]

        self._logger.debug("Hostname: " + self._hostname)
        self._logger.debug("Device Id: " + self._device_id)
        self._logger.debug("Shared Access Key: " + self._shared_access_key)

        self._mqtt = None

    def connect(self):
        """Connects to Azure IoT Central
        """
        self._mqtt = IoT_MQTT(self._hostname, self._device_id, self._shared_access_key, self._token_expires, self._logger)

        self._wire_up_events()

        self._mqtt.connect()

    def disconnect(self):
        """Disconnects from the MQTT broker
        """
        if self._mqtt is not None:
            self._mqtt.disconnect()

    def is_connected(self) -> bool:
        """Gets if there is an open connection to the MQTT broker
        """
        if self._mqtt is not None:
            return self._mqtt.is_connected()

        return False

    def loop(self):
        """Listens for MQTT messages
        """
        if self._mqtt is not None:
            self._mqtt.loop()

    def _wire_up_events(self):
        if self._mqtt is None:
            return

        for event_name in self._events:
            callback = self._events[event_name]
            if event_name == IoTHubDevice.DIRECT_METHOD_EVENT_NAME:
                self._mqtt.on(IoT_MQTT.DIRECT_METHOD_EVENT_NAME, callback)
            elif event_name == IoTHubDevice.CONNECTION_STATUS_EVENT_NAME:
                self._mqtt.on(IoT_MQTT.CONNECTION_STATUS_EVENT_NAME, callback)
            elif event_name == IoTHubDevice.CLOUD_TO_DEVICE_MESSAGE_RECEIVED_EVENT_NAME:
                self._mqtt.on(IoT_MQTT.CLOUD_TO_DEVICE_MESSAGE_RECEIVED_EVENT_NAME, callback)
            elif event_name == IoTHubDevice.TWIN_DESIRED_PROPERTIES_UPDATED_EVENT_NAME:
                self._mqtt.on(IoT_MQTT.TWIN_UPDATED_EVENT_NAME, callback)

    def on(self, event_name, callback):
        """Subscribe to a named event, and when that event happens callback is called

        The available events are:

        IoTHubDevice.DIRECT_METHOD_EVENT_NAME
        IoTHubDevice.TWIN_DESIRED_PROPERTIES_UPDATED_EVENT_NAME
        IoTHubDevice.CONNECTION_STATUS_EVENT_NAME
        IoTHubDevice.CLOUD_TO_DEVICE_MESSAGE_RECEIVED_EVENT_NAME
        """
        if event_name not in [
            IoTHubDevice.DIRECT_METHOD_EVENT_NAME,
            IoTHubDevice.TWIN_DESIRED_PROPERTIES_UPDATED_EVENT_NAME,
            IoTHubDevice.CONNECTION_STATUS_EVENT_NAME,
            IoTHubDevice.CLOUD_TO_DEVICE_MESSAGE_RECEIVED_EVENT_NAME,
        ]:
            return

        super(IoTHubDevice, self).on(event_name, callback)

        self._wire_up_events()

    def send_device_to_cloud_message(self, message, system_properties=None):
        """Sends a device to cloud message to the IoT Hub
        """
        if self._mqtt is not None:
            self._mqtt.send_device_to_cloud_message(message, system_properties)

    def update_twin(self, patch):
        """Updates the reported properties in the devices device twin
        """
        if self._mqtt is not None:
            self._mqtt.send_twin_patch(patch)
