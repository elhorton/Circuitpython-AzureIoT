import board, busio
# import adafruit_requests as requests
# import adafruit_hashlib as hashlib
# import adafruit_logging as logging
# from adafruit_minimqtt import MQTT
import adafruit_esp32spi.adafruit_esp32spi_socket as socket # how to make this platform agnostic? 
from connection import Connection
from secrets import secrets
from azureiotmqtt import Device, IOTCallbackInfo, IOTConnectType, IOTLogLevel, IOTQosLevel
import time
import json
import random
import neopixel

# ------------------------------------ START MAIN CODE ------------------------------------- #


def onconnect(info):
    print("- [onconnect] => status:" + str(info.getStatusCode()))

def onmessagesent(info):
    print("\t- [onmessagesent] => " + str(info.getPayload()))

def oncommand(info):
    print("Got a command!")
    print("- [oncommand] => " + info.getTag() + " => " + info.getPayload())
    commandName = info.getTag()
    if commandName == "SayHi":
      showText("Hi\nThere!")
    if commandName == "SendImage":
      showImage("smileyface.bmp")
      

def onsettingsupdated(info):
    print("- [onsettingsupdated] => " + info.getTag() + " => " + info.getPayload())

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

  # Keep the program running, otherwise the display is cleared
  #time.sleep(1000)
  return

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

  # # Move the whole group (which includes the TileGrid that has our image)
  # # The TileGrids inside the group have a relative position to the
  # # position of the group.
  # for i in range(0, 25, 5):
  #     group.x = i
  #     group.y = i
  #     time.sleep(.1)
  # # Then reset it back to 0,0
  # group.x, group.y = 0, 0

  # # You can scale groups by integer values, default is 1
  # group.scale = 2

  # # Each TileGrid inside a group has its own position relative to
  # # the position of the parent group.
  # # Move the TileGrid only, leaving group in same spot
  # for i in range(0, 25, 5):
  #     tile_grid.x = i
  #     tile_grid.y = i
  #     time.sleep(.1)

  # # If you had more TileGrids, you could add or remove them with:
  # # group.append()
  # # group.pop()
  # # group.insert()

  # If you close the file, it will not be able to display any more
  time.sleep(1)
  image_file.close()

  

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
connection = Connection()
wifi_manager = connection.connect(spi, True)

# Do the thing
id_scope = secrets['id_scope']
device_id = secrets['device_id']
primary_key = secrets['key']

my_device = Device(id_scope, primary_key, device_id, IOTConnectType.IOTC_CONNECT_SYMM_KEY, socket, connection, wifi_manager)

my_device.connect()

my_device.on("ConnectionStatus", onconnect)
my_device.on("MessageSent", onmessagesent)
my_device.on("Command", oncommand)
my_device.on("SettingsUpdated", onsettingsupdated)

while my_device.isConnected():
    my_device.doNext() # do the async work needed to be done for MQTT

    temp = 32.0 + random.uniform(-20.0, 20.0)
    state = {
        "TestTelemetry": random.randint(0, 1024),
        "Temperature": temp
    }
    my_device.sendState(json.dumps(state))