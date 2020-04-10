"""Connectivity to Azure IoT Central
"""

from adafruit_esp32spi.adafruit_esp32spi_wifimanager import ESPSPI_WiFiManager
from device_registration import DeviceRegistration
from iot_mqtt import IoT_MQTT
import adafruit_logging as logging


class IoTCentralDevice:
    """A device client for the Azure IoT Central service
    """

    # pylint: disable=R0913
    def __init__(
        self, wifi_manager: ESPSPI_WiFiManager, id_scope: str, device_id: str, key: str, token_expires: int = 21600, logger: logging = None
    ):
        self._wifi_manager = wifi_manager
        self._id_scope = id_scope
        self._device_id = device_id
        self._key = key
        self._token_expires = token_expires
        self._logger = logger
        self._device_registration = None
        self._mqtt = None
        self._events = {
            IoT_MQTT.MESSAGE_SENT_EVENT_NAME: None,
            IoT_MQTT.CONNECTION_STATUS_EVENT_NAME: None,
            IoT_MQTT.COMMAND_EVENT_NAME: None,
            IoT_MQTT.SETTING_UPDATED_EVENT_NAME: None,
        }

    # pylint: disable=C0103
    def on(self, event_name: str, callback):
        """Subscribe to a named event, and when that event happens callback is called

        The available events are:

        MessageSent
        ConnectionStatus
        Command
        SettingUpdated
        """
        self._events[event_name] = callback

        if self._mqtt is not None:
            self._mqtt.on(event_name, callback)

    def connect(self):
        """Connects to Azure IoT Central
        """
        self._device_registration = DeviceRegistration(self._wifi_manager, self._id_scope, self._device_id, self._key, self._logger)
        hostname = self._device_registration.register_device(self._token_expires)
        self._mqtt = IoT_MQTT(hostname, self._device_id, self._key, self._token_expires, self._logger)

        for event_name, callback in self._events:
            if callback is not None:
                self._mqtt.on(event_name, callback)

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
