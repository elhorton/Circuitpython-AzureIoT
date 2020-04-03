# The MIT License (MIT)
#
# Copyright (c) 2020 Jim Bennett
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`circuitpython_esp32connection`
================================================================================

A WiFi connection helper for ESP32-based boards


* Author(s): Jim Bennett

Implementation Notes
--------------------

**Hardware:**

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
* Adafruit's Bus Device library:
  https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

# imports

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/jimbobbennett/Circuitpython_CircuitPython_ESP32Connection.git"

import time
import board
import busio
from digitalio import DigitalInOut
import adafruit_requests as requests
import adafruit_minimqtt as MQTT
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_ntp import NTP
import adafruit_logging as logging


def __connect(cs_pin, ready_pin, reset_pin, ssid, password):
    logger = logging.getLogger("log")

    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, cs_pin, ready_pin, reset_pin)

    requests.set_socket(socket, esp)
    MQTT.set_socket(socket, esp)

    logger.debug("MAC addr: " + ", ".join([hex(i) for i in esp.MAC_address]))
    logger.debug("Connecting to AP...")

    while not esp.is_connected:
        try:
            esp.connect_AP(ssid, password)
        except RuntimeError as err:
            logger.debug("could not connect to AP, retrying: " + str(err))
            continue

    logger.info("Connected to " + str(esp.ssid, "utf-8") + "\tRSSI: " + str(esp.rssi))
    logger.debug("My IP address is " + esp.pretty_ip(esp.ip_address))

    logger.debug("Setting time")

    ntp = NTP(esp)
    while not ntp.valid_time:
        ntp.set_time()
        logger.debug("Failed to obtain time, retrying in 1 second...")
        time.sleep(1)

    logger.info("Time: " + str(time.time()))


def connect(ssid, password):
    """
    Connects to WiFi.

    This currently supports the PyBadge with Airlift Featherwing, and PyPortals
    """
    try:
        esp32_cs = DigitalInOut(board.ESP_CS)
        esp32_ready = DigitalInOut(board.ESP_BUSY)
        esp32_reset = DigitalInOut(board.ESP_RESET)
    except AttributeError:
        esp32_cs = DigitalInOut(board.D13)
        esp32_ready = DigitalInOut(board.D11)
        esp32_reset = DigitalInOut(board.D12)

    __connect(esp32_cs, esp32_ready, esp32_reset, ssid, password)
