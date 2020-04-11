# pylint: disable=C0114, C0116, C0103
import random
import time
from secrets import secrets
import board
import digitalio
from esp32connection import Connection
from iot_mqtt import IoTResponse
from gamepadshift import GamePadShift

# Set up wifi connection
CONNECTION = Connection()
WIFI_MANAGER = CONNECTION.connect(secrets)

TEST_IOT_CENTRAL = "TestIoTCentral"
TEST_IOT_HUB = "TestIoTHub"

TO_TEST = TEST_IOT_HUB

# Pybadge buttons
BUTTON_A = 2
pad = GamePadShift(
    digitalio.DigitalInOut(board.BUTTON_CLOCK), digitalio.DigitalInOut(board.BUTTON_OUT), digitalio.DigitalInOut(board.BUTTON_LATCH)
)


def connection_status_changed(connected):
    print("Received connected: ", str(connected))


if TO_TEST == TEST_IOT_HUB:
    from iothub_device import IoTHubDevice
    import json

    DEVICE_CONNECTION_STRING = secrets["device_connection_string"]

    MY_DEVICE = IoTHubDevice(DEVICE_CONNECTION_STRING)

    def direct_method_called(method_name, data) -> IoTResponse:
        print("Received direct method: " + method_name + " => " + str(data))
        return IoTResponse(200, "OK")

    def cloud_to_device_message_received(body: str, properties: dict):
        print("Received cloud to device message: " + body + " => " + json.dumps(properties))

    def device_twin_desired_updated(property_name: str, property_value, version: int) -> IoTResponse:
        print("Received device twin desired update: version " + str(version) + " => " + property_name + ":" + str(property_value))
        return IoTResponse(200, "OK")

    def device_twin_reported_updated(property_name: str, property_value, version: int) -> IoTResponse:
        print("Received device twin reported update: version " + str(version) + " => " + property_name + ":" + str(property_value))
        return IoTResponse(200, "OK")

    MY_DEVICE.on_connection_status_changed = connection_status_changed
    MY_DEVICE.on_direct_method_called = direct_method_called
    MY_DEVICE.on_cloud_to_device_message_received = cloud_to_device_message_received
    MY_DEVICE.on_device_twin_desired_updated = device_twin_desired_updated
    MY_DEVICE.on_device_twin_reported_updated = device_twin_reported_updated

    def check_buttons(btns):
        if (btns & BUTTON_A) > 0:
            print("Button A pressed")
            MY_DEVICE.update_twin(json.dumps({"Foo": "Bar" + str(random.randint(0, 100))}))

    current_buttons = pad.get_pressed()
    last_read = 0

    MY_DEVICE.connect()

    while MY_DEVICE.is_connected():
        MY_DEVICE.loop()  # do the async work needed to be done for MQTT

        # Do whatever
        if (last_read + 0.1) < time.monotonic():
            buttons = pad.get_pressed()
            last_read = time.monotonic()
        if current_buttons != buttons:
            check_buttons(buttons)
            current_buttons = buttons

        # sample of sending simulated telemetry
        temp = 32.0 + random.uniform(-20.0, 20.0)
        state = {"TestTelemetry": random.randint(0, 1024), "Temperature": temp}
        MY_DEVICE.send_device_to_cloud_message(json.dumps(state))
        time.sleep(1)

elif TO_TEST == TEST_IOT_CENTRAL:
    import terminalio
    import displayio
    import json
    from adafruit_display_text import label
    from iotcentral_device import IoTCentralDevice

    ID_SCOPE = secrets["id_scope"]
    DEVICE_ID = secrets["device_id"]
    PRIMARY_KEY = secrets["key"]

    # function for showing text on the PyPortal screen
    def showText(textToShow):

        # You must provide the text or the max_glyphs length, or both.
        # If no max_glyphs specified, the maximum is set to length of text
        # max_glyphs is the max amount of characters the text can contain
        text_area = label.Label(
            terminalio.FONT,
            text=textToShow,
            max_glyphs=50,  # Optionally allow longer text to be added
            color=0xFFFF00,
            x=20,  # Pixel offsets from (0, 0) the top left
            y=20,
            line_spacing=1,  # Distance between lines
        )

        board.DISPLAY.show(text_area)

        # You can modify the x and y coordinates and it will
        # immediately update the position
        for i in range(0, 50, 10):
            text_area.y += i
            text_area.x += i
            time.sleep(0.5)

        # Change the text color
        text_area.color = 0xFF0000
        # Add to text
        text_area.text = text_area.text + "!!!"

    # function to show an image on the PyPortal screen
    def showImage(imageFile):

        image_file = open(imageFile, "rb")
        bitmap_contents = displayio.OnDiskBitmap(image_file)

        tile_grid = displayio.TileGrid(
            bitmap_contents,
            pixel_shader=displayio.ColorConverter(),
            default_tile=0,
            x=0,  # Position relative to its parent group
            y=0,
            width=1,  # Number of tiles in the grid
            height=1,
            # tile_width=500,  # Number of tiles * tile size must match BMP size
            # tile_height=431,  # None means auto size the tiles
        )

        group = displayio.Group()
        group.append(tile_grid)
        board.DISPLAY.show(group)
        time.sleep(1)
        image_file.close()

    MY_DEVICE = IoTCentralDevice(WIFI_MANAGER, ID_SCOPE, DEVICE_ID, PRIMARY_KEY)

    def command_executed(command_name, data) -> IoTResponse:
        print("Received command: " + command_name + " => " + str(data))

        if command_name == "SayHi":
            showText("Hi\nThere!")
        if command_name == "SendImage":
            showImage("smileyface.bmp")

        return IoTResponse(200, "OK")

    def property_changed(property_name: str, property_value, version) -> IoTResponse:
        print("Received property update: version " + str(version) + " => " + property_name + ":" + str(property_value))
        return IoTResponse(200, "OK")

    MY_DEVICE.on_command_executed = command_executed
    MY_DEVICE.on_connection_status_changed = connection_status_changed
    MY_DEVICE.on_property_changed = property_changed

    def check_buttons(btns):
        if (btns & BUTTON_A) > 0:
            print("Button A pressed")
            MY_DEVICE.send_property("test_property", str(random.randint(0, 100)))

    current_buttons = pad.get_pressed()
    last_read = 0

    MY_DEVICE.connect()

    while MY_DEVICE.is_connected():
        MY_DEVICE.loop()  # do the async work needed to be done for MQTT

        if (last_read + 0.1) < time.monotonic():
            buttons = pad.get_pressed()
            last_read = time.monotonic()
        if current_buttons != buttons:
            check_buttons(buttons)
            current_buttons = buttons

        # sample of sending simulated telemetry
        temp = 32.0 + random.uniform(-20.0, 20.0)
        state = {"TestTelemetry": random.randint(0, 1024), "Temperature": temp}
        MY_DEVICE.send_telemetry(state)
        time.sleep(1)
