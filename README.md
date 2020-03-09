# Circuitpython-AzureIoT

A library for connecting to AzureIoT using Circuitpython. Still under construction!

## About this library

This is an adaptation of an [existing Micropython library for IoT Central](https://github.com/obastemur/iot_client); however, instead of using Micropython, this library uses Adafruit's Circuitpython. 

It is structured as follows: 
- `code.py` runs automatically whenever the Circuitpython board restarts. This is where the main application code should live. This currently has a very simple sample application sending telemetry and receiving commands from an IoT Central application. 
- `azureiotmqtt.py` contains the library for connecting to Azure IoT. 
- `CircuitpythonSampleTemplate.json` is the sample device template with the capability models needed for this application. It exposes two telemetry points and two commands:
    - `TestTelemetry` is just a random number
    - `Temperature` is a randomly generated temperature value
    - `SayHi` displays the text "Hi There!" on the screen if using the PyPortal device
    - Similarly, `SendImage` prompts the Pyportal device to show an image on the screen. In the case of this application, it's the `smileyface.bmp` file in this repo. 
- This application obtains user-specific info-- things like wifi connection ssid & password, device connection keys, device & scope id, etc.-- from the `secrets.py` file. You will have to edit this file with your own secrets or you can change how you obtain this info. We recommend never hardcoding this information. 

*TO DO*: 
1) Refactor the organization to make a lib folder containing:
    -  `azureiotmqtt.py`
    - `connection.py`
    - `defaultdict.py`
    - `hmac.py`
    - `parse.py`
    - `base64.py`
2) Refactor resources into a `media` folder:
    - `smileyface.bmp`
3) Provide more info on the connection details for the PyPortal and PyBadge (both use and ESP32 as a coprocessor for wifi functionality)
4) More code review and code cleaning


## Supported boards

You will need an Adafruit board with WiFi connectivity via an ESP32 chip, either on-board or using a separate board. This has been tested using:

* [Adafruit PyPortal](https://www.adafruit.com/product/4116)
* [AdaFruit PyBadge](https://www.adafruit.com/product/4200) with an [Airlift FeatherWing](https://www.adafruit.com/product/4264)


## Getting started with Circuitpython for Azure IoT

### Development Environment
#### Windows
#### Linux


## Usage

* Create an Azure IoT Central application, with a device template and a device. You can learn how to do this in the [Azure IoT Central docs](https://docs.microsoft.com/azure/iot-central/core/quick-deploy-iot-central/?WT.mc_id=iotc_circuitpython-github-jabenn). This application will need:

  * A device template. In this case, you should use the  `CircuitpythonSampleTemplate` from this repo, or create your own as you adapt this sample. 

  * A device using this template

* Download the latest version of the Adafruit CircuitPython libraries from the [releases page](https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases)

* Copy the following Adafruit Circuitpython libraries to the `lib` folder on your CircuitPython device

    | Name                  | Type   |
    | --------------------- | ------ |
    | adafruit_minimqtt.mpy | File   |
    | adafruit_logging.mpy  | File   |
    | adafruit_binascii.mpy | File   |
    | adafruit_requests.mpy | File   |
    | adafruit_hashlib      | Folder |
    | adafruit_esp32spi     | Folder |
    | adafruit_bus_device   | Folder |

* Copy the code from this repo to the device

* Edit 'secrets.py` to include your WiFi SSID and password, as well as the ID Scope, Device ID and Key for your device

* The device will reboot, connect to WiFi and connect to Azure IoT Central


