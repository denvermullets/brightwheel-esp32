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
import displayio
from adafruit_display_text.label import Label
from adafruit_display_shapes.rect import Rect
import terminalio

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



display = board.DISPLAY
display.auto_refresh = False

def create_full_display(entries):
    group = displayio.Group()

    # Background
    bg = Rect(0, 0, display.width, display.height, fill=0x000000)
    group.append(bg)

    # Title
    title = Label(terminalio.FONT, text="Beau's Day", color=0x00FF00, x=5, y=5)
    group.append(title)

    y = 20
    line_spacing = 12
    max_width = 40  # approx chars per line
    max_height = display.height - 20

    for entry in entries:
        if y > max_height:
            break

        # Find second colon
        colon_positions = [pos for pos, char in enumerate(entry) if char == ":"]
        if len(colon_positions) >= 2:
            second_colon_index = colon_positions[1]
            time_and_action = entry[:second_colon_index + 1].strip()
            message = entry[second_colon_index + 1:].strip()
        else:
            time_and_action = entry.strip()
            message = ""

        # First line: time + action (cyan)
        time_label = Label(terminalio.FONT, text=time_and_action, color=0x00FFFF, x=5, y=y)
        group.append(time_label)
        y += line_spacing

        # Second line(s): message (white, word-wrapped)
        if message:
            words = message.split()
            current = ""
            lines = []

            for word in words:
                test = current + " " + word if current else word
                if len(test) <= max_width:
                    current = test
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)

            for line in lines:
                if y > max_height:
                    break
                label = Label(terminalio.FONT, text=line, color=0xFFFFFF, x=5, y=y)
                group.append(label)
                y += line_spacing

        # Extra space between entries
        y += 4

    # Footer
    footer = f"{len(entries)} events"
    footer_label = Label(terminalio.FONT, text=footer, color=0x888888, x=5, y=display.height - 10)
    group.append(footer_label)

    return group

# Once JSON is loaded
group = create_full_display(json)
display.root_group = group
display.refresh()

# Wait before next update
while True:
    time.sleep(60 * 5)

