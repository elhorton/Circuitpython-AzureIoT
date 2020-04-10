"""MQTT client for Azure IoT
"""

import json
import time
from adafruit_minimqtt import MQTT
import circuitpython_parse as parse
from listener import Listener
from constants import constants
from device_registration import DeviceRegistration
import adafruit_logging as logging


class IOTCallbackInfo:
    """Info passed to subscribing methods after an MQTT message
    """

    # pylint: disable=R0913
    def __init__(self, event_name, payload, tag, status, msg_id):
        self._event_name = event_name
        self._payload = payload
        self._tag = tag
        self._status = status
        self._response_code = None
        self._response_message = None
        self._msg_id = msg_id

    def set_response(self, response_code, response_message):
        """Set the response to send to IoT Central
        """
        self._response_code = response_code
        self._response_message = response_message

    def get_event_name(self):
        """Get the MQTT event name
        """
        return self._event_name

    def get_payload(self):
        """Get the MQTT message payload
        """
        return self._payload

    def get_tag(self):
        """Get the MQTT message tag
        """
        return self._tag

    def get_status_code(self):
        """Get the MQTT status code
        """
        return self._status

    def get_response_code(self):
        """Get the MQTT response code
        """
        return self._response_code

    def get_response_message(self):
        """Get the MQTT response message
        """
        return self._response_message

    def get_message_id(self):
        """Get the MQTT message id
        """
        return self._msg_id


# pylint: disable=R0902
class IoT_MQTT(Listener):
    """MQTT client for Azure IoT
    """

    _iotc_api_version = constants["iotcAPIVersion"]

    def _gen_sas_token(self):
        token_expiry = int(time.time() + self._token_expires)
        uri = self._hostname + "%2Fdevices%2F" + self._device_id
        signed_hmac_sha256 = DeviceRegistration.compute_derived_symmetric_key(self._key, uri + "\n" + str(token_expiry))
        signature = parse.quote(signed_hmac_sha256, "~()*!.'")
        if signature.endswith("\n"):  # somewhere along the crypto chain a newline is inserted
            signature = signature[:-1]
        token = "SharedAccessSignature sr={}&sig={}&se={}".format(uri, signature, token_expiry)
        return token

    # Workaround for https://github.com/adafruit/Adafruit_CircuitPython_MiniMQTT/issues/25
    def _try_create_mqtt_client(self, hostname):
        self._mqtts = MQTT(
            broker=hostname,
            username=self._username,
            password=self._passwd,
            port=8883,
            keep_alive=120,
            is_ssl=True,
            client_id=self._device_id,
            log=True,
        )

        self._mqtts.logger.setLevel(logging.INFO)

        # set actions to take throughout connection lifecycle
        self._mqtts.on_connect = self._on_connect
        self._mqtts.on_message = self._on_message
        self._mqtts.on_log = self._on_log
        self._mqtts.on_publish = self._on_publish
        self._mqtts.on_disconnect = self._on_disconnect

        # initiate the connection using the adafruit_minimqtt library
        self._mqtts.last_will()
        self._mqtts.connect()

    def _create_mqtt_client(self):
        try:
            self._try_create_mqtt_client(self._hostname)
        except ValueError:
            # Workaround for https://github.com/adafruit/Adafruit_CircuitPython_MiniMQTT/issues/25
            self._try_create_mqtt_client("https://" + self._hostname)

    # pylint: disable=C0103, W0613
    def _on_connect(self, client, userdata, _, rc):
        self._logger.info("- iotc :: _on_connect :: rc = " + str(rc))
        if rc == 0:
            self._mqtt_connected = True
        self._auth_response_received = True
        self._make_callback(IoT_MQTT.CONNECTION_STATUS_EVENT_NAME, userdata, "on_connect", rc, None)

    # pylint: disable=C0103, W0613
    def _on_log(self, client, userdata, level, buf):
        self._logger.info("mqtt-log : " + buf)
        if level <= 8:
            self._logger.error("mqtt-log : " + buf)

    def _on_disconnect(self, client, userdata, rc):
        self._logger.info("- iotc :: _on_disconnect :: rc = " + str(rc))
        self._auth_response_received = True

        if rc == 5:
            self._logger.error("on(disconnect) : Not authorized")
            self.disconnect()

        if rc == 1:
            self._mqtt_connected = False

        if rc != 5:
            self._make_callback(IoT_MQTT.CONNECTION_STATUS_EVENT_NAME, userdata, "on_disconnect", rc, None)

    def _on_publish(self, client, data, topic, msg_id):
        self._logger.info("- iotc :: _on_publish :: " + str(data))
        if data is None:
            data = ""

        if msg_id is not None and (str(msg_id) in self._messages) and self._messages[str(msg_id)] is not None:
            self._make_callback("MessageSent", self._messages[str(msg_id)], data, 0, None)
            if str(msg_id) in self._messages:
                del self._messages[str(msg_id)]

    # pylint: disable=W0703, W0702
    def _echo_desired(self, msg, topic):
        self._logger.debug("- iotc :: _echo_desired :: " + topic)
        obj = None

        try:
            obj = json.loads(msg)
        except Exception as e:
            self._logger.error("ERROR: JSON parse for SettingsUpdated message object has failed. => " + msg + " => " + str(e))
            return 1

        version = None
        if "desired" in obj:
            obj = obj["desired"]

        if not "$version" in obj:
            self._logger.error("ERROR: Unexpected payload for settings update => " + msg)
            return 1

        version = obj["$version"]
        obj.pop("$version")

        self._make_callback(IoT_MQTT.TWIN_UPDATED_EVENT_NAME, json.dumps(obj), str(version), 0, None)

        return 0

    def _handle_device_twin_update(self, msg: str, topic: str):
        self._echo_desired(msg, topic)

    def _handle_direct_method(self, msg: str, topic: str):
        index = topic.find("$rid=")
        method_id = 1
        method_name = "None"
        if index == -1:
            self._logger.error("ERROR: C2D doesn't include topic id")
        else:
            method_id = topic[index + 5 :]
            topic_template = "$iothub/methods/POST/"
            len_temp = len(topic_template)
            method_name = topic[len_temp : topic.find("/", len_temp + 1)]

        ret = self._make_callback(self.DIRECT_METHOD_EVENT_NAME, msg, method_name, 0, None)
        ret_code = 200
        ret_message = "{}"
        if ret.get_response_code() is not None:
            ret_code = ret.get_response_code()
        if ret.get_response_message() is not None:
            ret_message = ret.get_response_message()

        next_topic = "$iothub/methods/res/{}/?$rid={}".format(ret_code, method_id)
        self._logger.info("C2D: => " + next_topic + " with data " + ret_message + " and name => " + method_name)
        self._send_common(next_topic, ret_message)

    def _handle_cloud_to_device_message(self, msg: str, topic: str):
        parts = topic.split("&")[1:]

        properties = {}
        for part in parts:
            key_value = part.split("=")
            properties[key_value[0]] = key_value[1]

        payload = json.dumps(properties)

        self._make_callback(self.CLOUD_TO_DEVICE_MESSAGE_RECEIVED_EVENT_NAME, payload, msg, 0, None)

    # pylint: disable=W0702, R0912
    def _on_message(self, client, msg_topic, payload):
        topic = ""
        msg = None

        print("Topic: ", str(msg_topic))
        self._logger.info("- iotc :: _on_message :: payload(" + str(payload) + ")")

        if payload is not None:
            try:
                msg = payload.decode("utf-8")
            except:
                msg = str(payload)

        if msg_topic is not None:
            try:
                topic = msg_topic.decode("utf-8")
            except:
                topic = str(msg_topic)

        if topic.startswith("$iothub/"):
            if topic.startswith("$iothub/twin/PATCH/properties/desired/") or topic.startswith("$iothub/twin/res/200/?$rid="):
                self._handle_device_twin_update(str(msg), topic)
            elif topic.startswith("$iothub/methods"):
                self._handle_direct_method(str(msg), topic)
            else:
                if not topic.startswith("$iothub/twin/res/"):  # not twin response
                    self._logger.error("ERROR: unknown twin! - {}".format(msg))
        elif topic.startswith("devices/{}/messages/devicebound".format(self._device_id)):
            self._handle_cloud_to_device_message(str(msg), topic)
        else:
            self._logger.error("ERROR: (unknown message) - {}".format(msg))

    def _send_common(self, topic, data) -> None:
        self._logger.debug("Sending message on topic: " + topic)
        self._logger.debug("Sending message: " + str(data))
        self._mqtts.publish(topic, data)

    def _get_device_settings(self) -> None:
        self._logger.info("- iotc :: _get_device_settings :: ")
        self.loop()
        self._send_common("$iothub/twin/GET/?$rid=0", " ")

    # pylint: disable=R0913
    def _make_callback(self, event_name: str, payload, tag, status, msg_id) -> IOTCallbackInfo:
        self._logger.info("- iotc :: self._make_callback :: " + event_name)
        cb = IOTCallbackInfo(event_name, payload, tag, status, msg_id)

        if event_name in self._events and self._events[event_name] is not None:
            self._events[event_name](cb)

        return cb

    MESSAGE_SENT_EVENT_NAME = "MessageSent"
    CONNECTION_STATUS_EVENT_NAME = "ConnectionStatus"
    DIRECT_METHOD_EVENT_NAME = "DirectMethod"
    CLOUD_TO_DEVICE_MESSAGE_RECEIVED_EVENT_NAME = "CloudToDeviceMessageReceived"
    SETTING_UPDATED_EVENT_NAME = "SettingUpdated"
    TWIN_UPDATED_EVENT_NAME = "TwinUpdated"

    # pylint: disable=R0913
    def __init__(self, hostname: str, device_id: str, key: str, token_expires: int = 21600, logger: logging = None):
        """Create the Azure IoT MQTT client
        :param str hostname: The hostname of the MQTT broker to connect to, get this by registering the device
        :param str device_id: The device ID of the device to register
        :param str key: The primary or secondary key of the device to register
        :param int token_expires: The number of seconds till the token expires, defaults to 6 hours
        :param adafruit_logging logger: The logger
        """
        super(IoT_MQTT, self).__init__()

        self._mqtt_connected = False
        self._auth_response_received = False
        self._mqtts = None
        self._device_id = device_id
        self._hostname = hostname
        self._key = key
        self._messages = {}
        self._token_expires = token_expires
        self._username = "{}/{}/api-version={}".format(self._hostname, device_id, self._iotc_api_version)
        self._passwd = self._gen_sas_token()
        self._logger = logger if logger is not None else logging.getLogger("log")
        self._events = {
            IoT_MQTT.MESSAGE_SENT_EVENT_NAME: None,
            IoT_MQTT.CONNECTION_STATUS_EVENT_NAME: None,
            IoT_MQTT.DIRECT_METHOD_EVENT_NAME: None,
            IoT_MQTT.SETTING_UPDATED_EVENT_NAME: None,
            IoT_MQTT.CLOUD_TO_DEVICE_MESSAGE_RECEIVED_EVENT_NAME: None,
            IoT_MQTT.TWIN_UPDATED_EVENT_NAME: None,
        }

    def connect(self):
        """Connects to the MQTT broker
        """
        self._logger.info("- iotc :: connect :: " + self._hostname)

        self._create_mqtt_client()

        self._logger.info(" - iotc :: connect :: created mqtt client. connecting..")
        while self._auth_response_received is None:
            self.loop()

        self._logger.info(" - iotc :: connect :: on_connect must be fired. Connected ? " + str(self.is_connected()))
        if not self.is_connected():
            return 1

        self._mqtt_connected = True
        self._auth_response_received = True

        self._mqtts.subscribe("devices/{}/messages/events/#".format(self._device_id))
        self._mqtts.subscribe("devices/{}/messages/devicebound/#".format(self._device_id))
        self._mqtts.subscribe("$iothub/twin/PATCH/properties/desired/#")  # twin desired property changes
        self._mqtts.subscribe("$iothub/twin/res/#")  # twin properties response
        self._mqtts.subscribe("$iothub/methods/#")

        if self._get_device_settings() == 0:
            self._make_callback(IoT_MQTT.SETTING_UPDATED_EVENT_NAME, None, None, 0, None)
        else:
            return 1

        return 0

    def disconnect(self):
        """Disconnects from the MQTT broker
        """
        if not self.is_connected():
            return

        self._logger.info("- iotc :: disconnect :: ")
        self._mqtt_connected = False
        self._mqtts.disconnect()

    def is_connected(self):
        """Gets if there is an open connection to the MQTT broker
        """
        return self._mqtt_connected

    def loop(self):
        """Listens for MQTT messages
        """
        if not self.is_connected():
            return

        self._mqtts.loop()

    def _send_common(self, topic, data):
        self._mqtts.publish(topic, data)

    def send_device_to_cloud_message(self, data, system_properties=None) -> None:
        """Send a device to cloud message from this device to Azure IoT Hub
        """
        self._logger.info("- iotc :: send_device_to_cloud_message :: " + data)
        topic = "devices/{}/messages/events/".format(self._device_id)

        if system_properties is not None:
            firstProp = True
            for prop in system_properties:
                if not firstProp:
                    topic += "&"
                else:
                    firstProp = False
                topic += prop + "=" + str(system_properties[prop])

        self._send_common(topic, data)
        self._make_callback(IoT_MQTT.MESSAGE_SENT_EVENT_NAME, data, None, 0, None)

    def send_twin_patch(self, data):
        """Send a patch for the reported properties of the device twin
        """
        self._logger.info("- iotc :: sendProperty :: " + data)
        topic = "$iothub/twin/PATCH/properties/reported/?$rid={}".format(int(time.time()))
        return self._send_common(topic, data)
