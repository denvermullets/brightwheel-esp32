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

ROTATE_SECONDS = 15
ENTRIES_PER_PAGE = 6

def paginate_entries_by_height(entries, line_height, screen_height, top_margin=20, bottom_margin=20):
    """Paginate entries dynamically based on how many lines fit per screen."""
    pages = []
    current_page = []
    current_y = top_margin

    for entry in entries:
        # Estimate number of lines this entry will take
        colon_positions = [pos for pos, c in enumerate(entry) if c == ":"]
        if len(colon_positions) >= 2:
            second_colon = colon_positions[1]
            time_and_action = entry[:second_colon + 1].strip()
            message = entry[second_colon + 1:].strip()
        else:
            time_and_action = entry.strip()
            message = ""

        # One line for time
        line_count = 1

        # Wrap message lines
        if message:
            max_chars = 40
            words = message.split()
            current = ""
            for word in words:
                test = current + " " + word if current else word
                if len(test) <= max_chars - 3:  # account for indent
                    current = test
                else:
                    line_count += 1
                    current = word
            if current:
                line_count += 1

        # Add padding between entries
        line_count += 1  # padding

        # Check if it fits on screen
        if current_y + (line_count * line_height) > screen_height - bottom_margin:
            pages.append(current_page)
            current_page = []
            current_y = top_margin

        current_page.append(entry)
        current_y += line_count * line_height

    # Add last page
    if current_page:
        pages.append(current_page)

    return pages

def create_display_page(entries_page, total_entries, page_index, total_pages):
    group = displayio.Group()

    # Background
    bg = Rect(0, 0, display.width, display.height, fill=0x000000)
    group.append(bg)

    # Title
    title = Label(terminalio.FONT, text="Beau's Day", color=0x00FF00, x=5, y=5)
    group.append(title)

    y = 20
    line_spacing = 12
    max_width = 40

    for entry in entries_page:
        if y > display.height - 20:
            break

        # Split entry
        colon_positions = [pos for pos, c in enumerate(entry) if c == ":"]
        if len(colon_positions) >= 2:
            second_colon = colon_positions[1]
            time_and_action = entry[:second_colon + 1].strip()
            message = entry[second_colon + 1:].strip()
        else:
            time_and_action = entry.strip()
            message = ""

        # Time + action line (cyan)
        time_label = Label(terminalio.FONT, text=time_and_action, color=0x00FFFF, x=5, y=y)
        group.append(time_label)
        y += line_spacing

        # Indented message lines (white)
        if message:
            indent = "   "
            words = message.split()
            current = ""
            lines = []

            for word in words:
                test = current + " " + word if current else word
                if len(indent + test) <= max_width:
                    current = test
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)

            for line in lines:
                if y > display.height - 20:
                    break
                label = Label(terminalio.FONT, text=indent + line, color=0xFFFFFF, x=5, y=y)
                group.append(label)
                y += line_spacing

        y += 4  # padding

    # Footer with page info
    footer_text = f"{total_entries} events | Page {page_index + 1} of {total_pages}"
    footer_label = Label(terminalio.FONT, text=footer_text, color=0x888888, x=5, y=display.height - 10)
    group.append(footer_label)

    return group


display = board.DISPLAY
display.auto_refresh = False

pages = paginate_entries_by_height(json, line_height=12, screen_height=display.height)
current_page = 0
last_switch = time.monotonic()

# First display
group = create_display_page(pages[current_page], len(json), current_page, len(pages))
display.root_group = group
display.refresh()

while True:
    now = time.monotonic()
    if len(pages) > 1 and now - last_switch >= ROTATE_SECONDS:
        current_page = (current_page + 1) % len(pages)
        group = create_display_page(pages[current_page], len(json), current_page, len(pages))
        display.root_group = group
        display.refresh()
        last_switch = now

    time.sleep(0.1)
