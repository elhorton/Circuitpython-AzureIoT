import board, busio
import json
from secrets import secrets
from digitalio import DigitalInOut
import adafruit_requests as requests
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager

class Connection:
    def __connect(self, spi, cs, ready, reset, log):
        esp = adafruit_esp32spi.ESP_SPIcontrol(spi, cs, ready, reset)

        requests.set_socket(socket, esp)

        if log:
            print("MAC addr:", [hex(i) for i in esp.MAC_address])
            print("Connecting to AP...")

        while not esp.is_connected:
            try:
                esp.connect_AP(secrets['ssid'], secrets['password'])
            except RuntimeError as e:
                if log:
                    print("could not connect to AP, retrying: ",e)
                continue

        if log:
            print("Connected to", str(esp.ssid, 'utf-8'), "\tRSSI:", esp.rssi)
            print("My IP address is", esp.pretty_ip(esp.ip_address))
        
        self.__wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets)

    def connect(self, spi, log = False):
        try:
            esp32_cs = DigitalInOut(board.ESP_CS)
            esp32_ready = DigitalInOut(board.ESP_BUSY)
            esp32_reset = DigitalInOut(board.ESP_RESET)
        except AttributeError:
            esp32_cs = DigitalInOut(board.D13)
            esp32_ready = DigitalInOut(board.D11)
            esp32_reset = DigitalInOut(board.D12)

        self.__connect(spi, esp32_cs, esp32_ready, esp32_reset, log)

        return self.__wifi
    
    def get_time(self, log = False):
        url = 'http://worldtimeapi.org/api/ip'
        has_time = False

        while not has_time:
            try:
                response = requests.get(url)
                response_json = json.loads(response.text)
                time_string = response_json['unixtime']
                has_time = True

                if  log:
                    print('time:', time_string)

                return int(time_string)
            except RuntimeError as e:
                if log:
                    print("could not connect to AP, retrying: ",e)
                continue        

