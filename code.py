# SPDX-FileCopyrightText: 2019 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
from os import getenv

import board
import busio
import neopixel
from digitalio import DigitalInOut

import displayio
from adafruit_display_text.label import Label
from adafruit_display_shapes.rect import Rect
import terminalio

from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi.adafruit_esp32spi_wifimanager import WiFiManager
from displayio import OnDiskBitmap, TileGrid

# Get wifi details and more from a settings.toml file
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
    pages = []
    current_page = []
    current_y = top_margin

    for entry in entries:
        colon_positions = [pos for pos, c in enumerate(entry) if c == ":"]
        if len(colon_positions) >= 2:
            second_colon = colon_positions[1]
            time_and_action = entry[:second_colon + 1].strip()
            message = entry[second_colon + 1:].strip()
        else:
            time_and_action = entry.strip()
            message = ""

        line_count = 1  # For time/action line

        if message:
            max_chars = 40
            words = message.split()
            current = ""
            for word in words:
                test = current + " " + word if current else word
                if len(test) <= max_chars - 3:
                    current = test
                else:
                    line_count += 1
                    current = word
            if current:
                line_count += 1

        line_count += 1  # padding

        if current_y + (line_count * line_height) > screen_height - bottom_margin:
            pages.append(current_page)
            current_page = []
            current_y = top_margin

        current_page.append(entry)
        current_y += line_count * line_height

    if current_page:
        pages.append(current_page)

    return pages

def create_display_page(entries_page, total_entries, page_index, total_pages):
    group = displayio.Group()

    # Background image
    try:
        bitmap = OnDiskBitmap("/background.bmp")
        tile_grid = TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
        group.append(tile_grid)
    except Exception as e:
        print("Failed to load background image:", e)
        group.append(Rect(0, 0, display.width, display.height, fill=0x000000))

    # Title
    title = Label(terminalio.FONT, text="Beau's Day", color=0x00FF00, x=5, y=5)
    group.append(title)

    y = 20
    line_spacing = 12
    max_width = 40

    for entry in entries_page:
        if y > display.height - 20:
            break

        colon_positions = [pos for pos, c in enumerate(entry) if c == ":"]
        if len(colon_positions) >= 2:
            second_colon = colon_positions[1]
            time_and_action = entry[:second_colon + 1].strip()
            message = entry[second_colon + 1:].strip()
        else:
            time_and_action = entry.strip()
            message = ""

        time_label = Label(terminalio.FONT, text=time_and_action, color=0x00FFFF, x=5, y=y)
        group.append(time_label)
        y += line_spacing

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

    footer_text = f"{total_entries} events | Page {page_index + 1} of {total_pages}"
    footer_label = Label(terminalio.FONT, text=footer_text, color=0x888888, x=5, y=display.height - 10)
    group.append(footer_label)

    return group

pages = paginate_entries_by_height(json, line_height=12, screen_height=display.height)
current_page = 0
last_switch = time.monotonic()

# Initial page
group = create_display_page(pages[current_page], len(json), current_page, len(pages))
display.root_group = group
display.refresh()

FETCH_INTERVAL = 300  # 5 minutes
last_fetch = time.monotonic()

while True:
    now = time.monotonic()

    # Check if it's time to fetch new data
    if now - last_fetch >= FETCH_INTERVAL:
        try:
            print("Refreshing data...")
            response = wifi.get(JSON_URL)
            json = response.json()
            pages = paginate_entries_by_height(json, line_height=12, screen_height=display.height)
            current_page = 0
            last_fetch = now

            # Show first page of new data
            group = create_display_page(pages[current_page], len(json), current_page, len(pages))
            display.root_group = group
            display.refresh()
            last_switch = now  # Reset page switch timer
        except OSError as e:
            print("Error during data refresh:", e)

    # Rotate page
    if len(pages) > 1 and now - last_switch >= ROTATE_SECONDS:
        current_page = (current_page + 1) % len(pages)
        group = create_display_page(pages[current_page], len(json), current_page, len(pages))
        display.root_group = group
        display.refresh()
        last_switch = now

    time.sleep(0.1)

