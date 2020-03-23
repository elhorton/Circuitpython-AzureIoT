import board, busio
import adafruit_esp32spi.adafruit_esp32spi_socket as socket 
from connection import Connection
from secrets import secrets
from azureiotmqtt import Device, IOTCallbackInfo, IOTConnectType, IOTLogLevel, IOTQosLevel
import time
import json
import random
import neopixel

# ------------------------------------ Listener functions ------------------------------------- #

def onconnect(info):
    print("Connection status: " + str(info.getStatusCode()))

def onmessagesent(info):
    print("Message sent: " + str(info.getPayload()))

# defining commands from an IoT Central application
def oncommand(info):
    print("Received command: " + info.getTag() + " => " + info.getPayload())
    commandName = info.getTag()
    if commandName == "SayHi":
      showText("Hi\nThere!")
    if commandName == "SendImage":
      showImage("smileyface.bmp")
    
    # # if using PyBadge, try the following:
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
    

def onsettingsupdated(info):
    print("Updating settings: " + info.getTag() + " => " + info.getPayload())

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
      time.sleep(.5)

  # Change the text color
  text_area.color = 0xFF0000
  # Add to text
  text_area.text = text_area.text + '!!!'
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
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
connection = Connection()
wifi_manager = connection.connect(spi, True) 


# Get info for your specific device configuration
id_scope = secrets['id_scope']
device_id = secrets['device_id']
primary_key = secrets['key'] 

# create your ESP32 wifi enabled device, pass in connection & wifi setup 
my_device = Device(id_scope, primary_key, device_id, IOTConnectType.IOTC_CONNECT_SYMM_KEY, socket, connection, wifi_manager)

my_device.connect()

my_device.on("ConnectionStatus", onconnect)
my_device.on("MessageSent", onmessagesent)
my_device.on("Command", oncommand) # write command handlers in the oncommand function
my_device.on("SettingsUpdated", onsettingsupdated)

while my_device.isConnected():
    my_device.doNext() # do the async work needed to be done for MQTT

    # Do whatever

    # sample of sending simulated telemetry
    temp = 32.0 + random.uniform(-20.0, 20.0)
    state = {
        "TestTelemetry": random.randint(0, 1024),
        "Temperature": temp
    }
    my_device.sendState(json.dumps(state))