# CircuitPython-AzureIoT

A library for connecting to AzureIoT using CircuitPython. Still under construction!

## About this library

This is an adaptation of an [existing MicroPython library for IoT Central](https://github.com/obastemur/iot_client); however, instead of using MicroPython, this library uses Adafruit's CircuitPython.

It is structured as follows:

- `code.py` runs automatically whenever the CircuitPython board restarts. This is where the main application code should live. This currently has a very simple sample application sending telemetry and receiving commands from an IoT Central application geared at the *PyPortal* or *PyBadge* device. 
- `azureiotmqtt.py` contains the library for connecting to Azure IoT.
- `CircuitPythonSampleTemplate.json` is the sample device template with the capability models needed for this application. This can be used to showcase the basics of IoT Central with the PyPortal device. It exposes two telemetry points and two commands:
  - `TestTelemetry` is just a random number
  - `Temperature` is a randomly generated temperature value
  - `SayHi` displays the text "Hi There!" on the screen if using the PyPortal device
  - Similarly, `SendImage` prompts the PyPortal or PyBadge device to show an image on the screen. In the case of this application, it's the `smileyface.bmp` file in this repo.
- This application obtains user-specific info-- things like wifi connection ssid & password, device connection keys, device & scope id, etc.-- from the `secrets.py` file. You will have to edit this file with your own secrets or you can change how you obtain this info. We recommend never hardcoding this information.
- This application also stores global constants for API versions in the `constants.py` file. This file can easily be expanded upon for your own needs.

*TO DO*:

1. Provide more info on how the connection works for the PyPortal and PyBadge (both use and ESP32 as a coprocessor for wifi functionality). This could be refactored to be separated from the device class as a future code improvement.
1. Fill in additional helpful information about the development environments, tips and tricks, additional possible errors.

## Supported boards

You will need an Adafruit board with WiFi connectivity via an ESP32 chip, either on-board or using a separate board. This has been tested using:

- [Adafruit PyPortal](https://www.adafruit.com/product/4116)
- [AdaFruit PyBadge](https://www.adafruit.com/product/4200) with an [Airlift FeatherWing](https://www.adafruit.com/product/4264)

## Getting started with CircuitPython for Azure IoT

### Development Environment

Luckily, working with Adafruit devices is pretty easy! This repo was built using VS Code, but the Mu editor is also quite popular with CircuitPython. The PyPortal device also has its own microSD storage, which makes developing and saving code on it much simpler. You can directly save files to the `CIRCUITPY` drive, and the device will auto-reload after it detects any code changes.

Overall, there are two components to think about when working with CircuitPython:

1) Your development machine and environment:
    - Text editor (VS Code, Mu, etc.)
    - The OS of the machine you're using (Windows, Linux, etc.)
2) A way to interact with your Adafruit device
    - Serial console (like [PuTTY](https://putty.org/)). You can use this to monitor any output from the device, use the Python REPL, or restart your programs.  
    - You will need a way to copy code from your development machine to your CircuitPython device.

## Usage

### Create IoT Central Application

- Create an Azure IoT Central application, with a device template and a device. You can learn how to do this in the [Azure IoT Central docs](https://docs.microsoft.com/azure/iot-central/core/quick-deploy-iot-central/?WT.mc_id=iotc_circuitpython-github-jabenn). This application will need:

  - A device template. In this case, you should use the  `CircuitPythonSampleTemplate` from this repo, or create your own as you adapt this sample.

  - In your IoT Central application, configure a device identity to use this template. For example, create a device with ID `MyPyPortal`, and deploy the `CircuitPythonSampleTemplate` to it.

  - Create a view associated with the Device Template in IoT Central so that you can test sending commands and seeing telemetry appear on the dashboard.
    - You can learn more about creating dashboards and views [here](https://docs.microsoft.com/azure/iot-central/core/howto-add-tiles-to-your-dashboard).

### Install CircuitPython code on your device

- Download the latest version of the Adafruit CircuitPython libraries from the [releases page](https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases)

- Copy the following Adafruit CircuitPython libraries to the `lib` folder on your CircuitPython device

    | Name                  | Type   |
    | --------------------- | ------ |
    | adafruit_minimqtt.mpy | File   |
    | adafruit_logging.mpy  | File   |
    | adafruit_binascii.mpy | File   |
    | adafruit_requests.mpy | File   |
    | adafruit_ntp.mpy      | File   |
    | neopixel_spi.mpy      | File   |
    | neopixel.mpy          | File   |
    | simpleio.mpy          | File   |
    | adafruit_hashlib      | Folder |
    | adafruit_esp32spi     | Folder |
    | adafruit_bus_device   | Folder |

- Download the latest version of the Adafruit Community CircuitPython libraries from the [releases page](https://github.com/adafruit/CircuitPython_Community_Bundle/releases)

- Copy the following Adafruit Community CircuitPython libraries to the `lib` folder on your CircuitPython device

    | Name                     | Type   |
    | ------------------------ | ------ |
    | circuitpython_base64.mpy | File   |
    | circuitpython_hmac.mpy   | File   |
    | circuitpython_parse.mpy  | File   |

- Copy the code from this repo to the device.

- Edit `secrets.py` to include your WiFi SSID and password, as well as the ID Scope, Device ID and Key for your device. This can be found within your IoT Central application by clicking on your Device and selecting `Connect` from the top options menu.

- Edit `constants.py` to include the API versions you'd like to use and any other global constants for your application.

- The device will reboot, connect to WiFi and connect to Azure IoT Central.

## Possible Errors

- This library does not currently have any restart logic built in. Consequently, a good first step at troubleshooting is to simply restart the device using CTRL + D in the serial console.
- Ensure that your connection info (wifi SSID and password, device scope, ID, and connection string) are correctly saved in your `secrets.py` file.

## Limitations

- Currently this library only supports symmetric key authentication. There is no support for X.509 Certificates.
