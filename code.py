from iothubdevice import IoTHubDevice
import board, busio, digitalio
from esp32connection import Connection
from secrets import secrets
from iotcentraldevice import IoTCentralDevice
from iot_mqtt import IOTCallbackInfo
from gamepadshift import GamePadShift
import time
import json
import random
import neopixel

# ------------------------------------ Listener functions ------------------------------------- #


def on_connect(info: IOTCallbackInfo):
    print("Connection status: " + str(info.get_status_code()))


def onmessagesent(info: IOTCallbackInfo):
    print("Message sent: " + str(info.get_payload()))


# defining commands from an IoT Central application
def oncommand(info: IOTCallbackInfo):
    print("Received command: " + info.get_tag() + " => " + info.get_payload())
    commandName = info.get_tag()
    if commandName == "SayHi":
        showText("Hi\nThere!")
    if commandName == "SendImage":
        showImage("smileyface.bmp")

    # # if using PyBadge, add the following:
    # global is_on
    # print("- [oncommand] => " + info.getTag() + " => " + str(info.getPayload()))

    # if is_on:
    #     neopixels[0] = (0, 0, 0)
    #     neopixels.show()
    #     is_on = False
    # else:
    #     neopixels[0] = (255, 255, 255)
    #     neopixels.show()
    #     is_on = True


def onsettingsupdated(info: IOTCallbackInfo):
    print("Updating settings: " + info.get_tag() + " => " + info.get_payload())


# function for showing text on the PyPortal screen
def showText(textToShow):
    import terminalio
    from adafruit_display_text import label

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
    return


# function to show an image on the PyPortal screen
def showImage(imageFile):
    import displayio

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


# -------------------------- Start Main Code -------------------------------- #

# Set up wifi connection
connection = Connection()
wifi_manager = connection.connect(secrets)


# Get info for your specific device configuration
id_scope = secrets["id_scope"]
device_id = secrets["device_id"]
primary_key = secrets["key"]
device_connection_string = secrets["device_connection_string"]

# create your ESP32 wifi enabled device, pass in connection & wifi setup
# my_device = IoTCentralDevice(wifi_manager, id_scope, primary_key, device_id)
my_device = IoTHubDevice(device_connection_string)


def on_direct_method(info: IOTCallbackInfo):
    print("Received direct method: " + info.get_tag() + " => " + info.get_payload())


def on_cloud_to_device_message(info: IOTCallbackInfo):
    print("Received cloud to device message: " + info.get_tag() + " => " + info.get_payload())


def on_twin_updated(info: IOTCallbackInfo):
    print("Received twin update message: " + info.get_tag() + " => " + info.get_payload())


my_device.on(IoTHubDevice.DIRECT_METHOD_EVENT_NAME, on_direct_method)
my_device.on(IoTHubDevice.CONNECTION_STATUS_EVENT_NAME, on_connect)
my_device.on(IoTHubDevice.CLOUD_TO_DEVICE_MESSAGE_RECEIVED_EVENT_NAME, on_cloud_to_device_message)
my_device.on(IoTHubDevice.TWIN_DESIRED_PROPERTIES_UPDATED_EVENT_NAME, on_twin_updated)
# my_device.on("MessageSent", onmessagesent)
# my_device.on("Command", oncommand)  # write command handlers in the oncommand function
# my_device.on("SettingsUpdated", onsettingsupdated)

# Pybadge buttons
BUTTON_A = 2
pad = GamePadShift(
    digitalio.DigitalInOut(board.BUTTON_CLOCK), digitalio.DigitalInOut(board.BUTTON_OUT), digitalio.DigitalInOut(board.BUTTON_LATCH)
)


def check_buttons(buttons):
    if (buttons & BUTTON_A) > 0:
        print("Button A pressed")
        my_device.update_twin(json.dumps({"Foo": "Bar2"}))


current_buttons = pad.get_pressed()
last_read = 0

my_device.connect()

while my_device.is_connected():
    my_device.loop()  # do the async work needed to be done for MQTT

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
    # my_device.send_device_to_cloud_message(json.dumps(state))
    time.sleep(1)
