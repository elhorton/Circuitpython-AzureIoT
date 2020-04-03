import board, busio
import time
from digitalio import DigitalInOut
import adafruit_requests as requests
import adafruit_minimqtt as MQTT
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_ntp import NTP


class Connection:
    def __connect(self, cs, ready, reset, ssid, password, log):
        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        esp = adafruit_esp32spi.ESP_SPIcontrol(spi, cs, ready, reset)

        requests.set_socket(socket, esp)
        MQTT.set_socket(socket, esp)

        if log:
            print("MAC addr:", [hex(i) for i in esp.MAC_address])
            print("Connecting to AP...")

        while not esp.is_connected:
            try:
                esp.connect_AP(ssid, password)
            except RuntimeError as e:
                if log:
                    print("could not connect to AP, retrying: ", e)
                continue

        if log:
            print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)
            print("My IP address is", esp.pretty_ip(esp.ip_address))

        ntp = NTP(esp)
        while not ntp.valid_time:
            ntp.set_time()
            print("Failed to obtain time, retrying in 1 seconds...")
            time.sleep(1)
        print("Time:", time.time())

    def connect(self, ssid, password, log=False):
        try:
            esp32_cs = DigitalInOut(board.ESP_CS)
            esp32_ready = DigitalInOut(board.ESP_BUSY)
            esp32_reset = DigitalInOut(board.ESP_RESET)
        except AttributeError:
            esp32_cs = DigitalInOut(board.D13)
            esp32_ready = DigitalInOut(board.D11)
            esp32_reset = DigitalInOut(board.D12)

        self.__connect(esp32_cs, esp32_ready, esp32_reset, ssid, password, log)
