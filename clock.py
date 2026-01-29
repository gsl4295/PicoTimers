try:
    from board_definitions.raspberry_pi_pico_w import GP10, GP11, GP16, GP17, GP18, GP0, LED
except ImportError:  # pragma: no cover
    # noinspection PyPackageRequirements
    from board import GP10, GP11, GP16, GP17, GP18, GP0, LED
from busio import SPI
from digitalio import DigitalInOut, Direction, Pull
import gc

from displayio import release_displays, Group, Bitmap, Palette, TileGrid
from terminalio import FONT
from fourwire import FourWire
from adafruit_display_text import label
from adafruit_display_text.scrolling_label import ScrollingLabel
from adafruit_st7735r import ST7735R

# noinspection PyPackageRequirements
from wifi import radio
# noinspection PyPackageRequirements
import socketpool
import ssl
from os import getenv

import adafruit_requests
import adafruit_ntp
from adafruit_datetime import datetime, timedelta
from time import sleep
import time, rtc


class PicoControl:
    def __init__(self):
        self.counter = 0
        mosi_pin = GP11
        clk_pin = GP10
        reset_pin = GP17
        cs_pin = GP18
        dc_pin = GP16
        release_displays()
        spi = SPI(clock=clk_pin, MOSI=mosi_pin)
        display_bus = FourWire(spi, command=dc_pin, chip_select=cs_pin, reset=reset_pin)
        self.display = ST7735R(display_bus, width=128, height=160, bgr=True)
        self.led = DigitalInOut(LED)
        self.led.direction = Direction.OUTPUT
        self.pool = socketpool.SocketPool(radio)
        # noinspection PyTypeChecker
        self.requests = adafruit_requests.Session(self.pool, ssl.create_default_context())
        self.launch: dict = {}
        self.name: str = ""
        self.t0: str = ""
        self.win_open: str = ""
        self.win_close: str = ""
        self.provider: str = ""
        self.vehicle: str = ""
        self.pad: str = ""
        self.lc: str = ""
        self.country: str = ""
        self.y: str = ""
        self.m: str = ""
        self.d: str = ""
        self.h: str = ""
        self.mi: str = ""
        self.dy: str = ""
        self.button = DigitalInOut(GP0)
        self.button.direction = Direction.INPUT
        self.button.pull = Pull.DOWN
        self.placeholder_setting: bool = False
        self.utc_delta: int = 0

    def led_toggle(self, toggle: bool):
        self.led.value = toggle

    # noinspection PyUnresolvedReferences
    @staticmethod
    def manage_memory(verbose=False):
        if verbose:
            old_memory_available = gc.mem_free()
            gc.collect()
            print(f"Memory cleaned: {old_memory_available} -> {gc.mem_free()} bytes free")
        else:
            gc.collect()

    def visuals(self, accent: tuple):
        # Add background with accent color
        splash = Group()
        self.display.root_group = splash
        color_bitmap = Bitmap(128, 160, 1)
        color_palette = Palette(1)
        color_palette[0] = (0, 0, 0)
        bg_sprite = TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
        splash.append(bg_sprite)

        countdown_text_group = Group(scale=3, x=20, y=30)
        self.countdown_text_area = label.Label(FONT, text="00:00", color=accent)
        countdown_text_group.append(self.countdown_text_area)
        splash.append(countdown_text_group)

        main_text_group = Group(scale=1, x=20, y=65)
        self.main_row_1 = label.Label(FONT, y=0, text="", color=accent)
        self.main_row_2 = label.Label(FONT, y=15, text="", color=accent)
        self.main_row_3 = label.Label(FONT, y=30, text="", color=accent)
        self.main_row_4 = label.Label(FONT, y=45, text="Pico Clock", color=accent)
        self.main_row_5 = label.Label(FONT, y=60, text="by gsl4295", color=accent)
        self.main_row_6 = label.Label(FONT, y=75, text="Loading...", color=accent)
        main_text_group.append(self.main_row_1)
        main_text_group.append(self.main_row_2)
        main_text_group.append(self.main_row_3)
        main_text_group.append(self.main_row_4)
        main_text_group.append(self.main_row_5)
        main_text_group.append(self.main_row_6)
        splash.append(main_text_group)

        print(f"Screen rendered with an accent of RGB value {accent}")

    @staticmethod
    def wifi_connect():
        while True:
            try:
                radio.connect(getenv("WIFI"), getenv("PASS"))
                print(f"Connected to the Internet via {getenv("WIFI")}")
                return
            except ConnectionError:
                print("No connection, trying again in 2 seconds")
                sleep(2)
                continue

    def get_time(self) -> int:
        # for startup alone when pico clock is not synced
        ntp = adafruit_ntp.NTP(self.pool, server="pool.ntp.org", tz_offset=-6)
        try:
            rtc.RTC().datetime = ntp.datetime
        except OSError:
            print("Reassigning time value didn't work, disregarding that code block")

        self.years = int(rtc.RTC().datetime.tm_year)
        self.months = int(rtc.RTC().datetime.tm_mon)
        self.days = int(rtc.RTC().datetime.tm_mday)
        self.hours = int(rtc.RTC().datetime.tm_hour)
        
        if self.hours > 12:
            self.hours -= 12
        
        self.italy_hrs = self.hours + 7
        
        if self.italy_hrs > 12:
            self.italy_hrs -= 12

        self.minutes = int(rtc.RTC().datetime.tm_min)
        self.seconds = int(rtc.RTC().datetime.tm_sec)
        return

    def countdown_loop(self, update_time=15, display_interval=15):
        # http_time defines the time (seconds) that it takes for countdown_loop() to break out of the loop.
        # display_interval defines the time (seconds) that the display has before refreshing.

        num_cycles = int(update_time / display_interval)

        for cycle in range(num_cycles):
            self.countdown_text_area.text = f"{self.hours:02}:{self.minutes:02}"
            self.main_row_1.text = f"{self.months}/{self.days}/{self.years}"
            self.main_row_2.text = f""
            self.main_row_3.text = f""
            self.main_row_4.text = f""
            self.main_row_5.text = f"Time in Milan"
            self.main_row_6.text = f"{self.italy_hrs}:{self.minutes:02} (UTC+1)"

            self.counter += 1
            if self.counter == 1:
                print(f"Countdown active")

            sleep(display_interval)

    def run_loop(self, r=255, g=255, b=255):
        self.led_toggle(False)
        self.visuals((r, g, b))
        self.wifi_connect()
        while True:
            self.get_time()
            self.countdown_loop()
            self.manage_memory(verbose=False)


if __name__ == "__main__":
    print("System on internal power")
    control = PicoControl()
    control.run_loop()
