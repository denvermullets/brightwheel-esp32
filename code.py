# SPDX-FileCopyrightText: 2019 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
from os import getenv

import board
import busio
import neopixel
from digitalio import DigitalInOut

from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi.adafruit_esp32spi_wifimanager import WiFiManager

# Get wifi details and more from a settings.toml file
# tokens used by this Demo: CIRCUITPY_WIFI_SSID, CIRCUITPY_WIFI_PASSWORD
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")

print("ESP32 local time")

TIME_API = "http://worldtimeapi.org/api/ip"
JSON_URL = getenv("BRIGHTWHEEL_PROXY")

esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)


status_pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

wifi = WiFiManager(esp, ssid, password, status_pixel=status_pixel)

response = None
while True:
    try:
        print("Fetching json from", JSON_URL)
        response = wifi.get(JSON_URL)
        break
    except OSError as e:
        print("Failed to get data, retrying\n", e)
        continue

json = response.json()

while True:
    print(json)
    # sleep for 5 minutes
    time.sleep(60 * 5)
