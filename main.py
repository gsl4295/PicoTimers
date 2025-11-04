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
from adafruit_datetime import datetime, timedelta
from time import sleep


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
        self.manual_setting: bool = False
        self.utc_delta: int = 0
        self.time_response: dict = {}
        self.countdown_text_area = None
        self.main_row_1 = None
        self.main_row_2 = None
        self.main_row_3 = None
        self.main_row_4 = None
        self.main_row_5 = None
        self.main_row_6 = None
        self.main_row_7 = None

    def led_toggle(self, toggle: bool):
        self.led.value = toggle

    # noinspection PyUnresolvedReferences
    @staticmethod
    def manage_memory(verbose=False):
        # Memory cleanup.
        # verbose (bool) - default: False - Self-explanatory

        old_memory_available = gc.mem_free()
        gc.collect()
        new_memory_available = gc.mem_free()
        if verbose:
            print(f"Memory cleaned: {old_memory_available} -> {new_memory_available} bytes free")
        return old_memory_available, new_memory_available


    def visuals(self, accent: tuple):
        # Sets up the screen's color scheme, all 7 rows of data, and the countdown section.
        # accent (tuple) - default: None - The accent of the screen, expressed in hexcode notation.

        # Add background
        splash = Group()
        self.display.root_group = splash
        color_bitmap = Bitmap(128, 160, 1)
        color_palette = Palette(1)
        color_palette[0] = accent
        bg_sprite = TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
        splash.append(bg_sprite)

        # Create black rectangle
        # This visually makes the purple background look like just a border
        inner_bitmap = Bitmap(118, 120, 1)
        inner_palette = Palette(1)
        inner_palette[0] = 0x000000  # Black
        inner_sprite = TileGrid(inner_bitmap, pixel_shader=inner_palette, x=5, y=35)
        splash.append(inner_sprite)

        countdown_text_group = Group(scale=2, x=16, y=18)
        self.countdown_text_area = label.Label(FONT, text="", color=0x000000)
        countdown_text_group.append(self.countdown_text_area)
        splash.append(countdown_text_group)

        max_chars = 17

        main_text_group = Group(scale=1, x=16, y=50)
        self.main_row_1 = ScrollingLabel(FONT, y=0, animate_time=0.5, max_characters=max_chars, text="", color=accent)
        self.main_row_2 = ScrollingLabel(FONT, y=15, animate_time=0.5, max_characters=max_chars, text="Data by rocket",
                                         color=accent)
        self.main_row_3 = ScrollingLabel(FONT, y=30, animate_time=0.5, max_characters=max_chars, text="launch.live",
                                         color=accent)
        self.main_row_4 = ScrollingLabel(FONT, y=45, animate_time=0.5, max_characters=max_chars,
                                         text="---------------", color=accent)
        self.main_row_5 = ScrollingLabel(FONT, y=60, animate_time=0.5, max_characters=max_chars,
                                         text="PicoLaunchTimer", color=accent)
        self.main_row_6 = label.Label(FONT, y=75, text="Version 0.3", color=accent)
        self.main_row_7 = label.Label(FONT, y=90, text="Loading...", color=accent)
        main_text_group.append(self.main_row_1)
        main_text_group.append(self.main_row_2)
        main_text_group.append(self.main_row_3)
        main_text_group.append(self.main_row_4)
        main_text_group.append(self.main_row_5)
        main_text_group.append(self.main_row_6)
        main_text_group.append(self.main_row_7)
        splash.append(main_text_group)

        print(f"Screen rendered with an accent of RGB value {accent}")

    def update_scrolls(self):
        self.main_row_1.update()
        self.main_row_2.update()
        self.main_row_3.update()
        self.main_row_4.update()
        self.main_row_5.update()
        return "Screen scrolled"

    @staticmethod
    def wifi_connect():
        while True:
            try:
                radio.connect(getenv("WIFI"), getenv("PASS"))
                print(f"Connected to the Internet via {getenv("WIFI")}")
                return "Connected"
            except ConnectionError:
                print("No connection, trying again in 2 seconds")
                sleep(2)
                continue

    def get_utc_delta(self, country="America", zone="Chicago", st_delta=-6) -> int:
        # Gets the UTC delta from https://timeapi.io
        # country (str) - default: "America"
        # zone (str) - default: "Chicago"
        # st_delta (int) - default: -6 - the UTC delta when a specific timezone is in *standard time.*

        # noinspection HttpUrlsUsage
        self.time_response = self.requests.get(f"http://timeapi.io/api/time/current/zone?timeZone={country}%2F{zone}")
        time_content = self.time_response.json()
        self.time_response.close()
        utc_delta_bool = time_content["dstActive"]

        if utc_delta_bool:
            dst_delta = 1
        else:
            dst_delta = 0

        total_delta = dst_delta + st_delta
        print(f"Received a universal time delta from timeapi.io: {total_delta}")
        return total_delta

    def get_launch_info(self):
        # Gets the latest launch data from https://rocketlaunch.live/api

        response = self.requests.get("https://fdo.rocketlaunch.live/json/launches/next/1")
        content = response.json()
        response.close()
        try:
            self.launch = content["result"][0]
        except (AttributeError, KeyError):
            self.launch = {
                "t0": "ERROR t0",
                "win_open": "ERROR win_open",
                "name": "ERROR name",
                "vehicle": {"name": "ERROR vehicle/name"},
                "pad": {
                    "name": "ERROR pad/name",
                    "location": {"name": "ERROR pad/location/name", "country": "ERROR pad/location/country"}
                }
            }

    def define_auto_vars(self):
        # Redefines the main variables of the countdown to the ones given from get_launch_info()

        self.t0 = self.launch["t0"]
        self.win_open = self.launch["win_open"]

        # If an official T-0 time isn't listed, but a window opening time is, use it instead
        if self.launch["t0"] is None and self.launch["win_open"] is not None:
            self.t0 = self.launch["win_open"]

        self.name = self.launch["name"]
        self.vehicle = self.launch["vehicle"]["name"]
        self.pad = self.launch["pad"]["name"]
        self.lc = self.launch["pad"]["location"]["name"]
        self.country = self.launch["pad"]["location"]["country"]

        d, t = self.t0[:-1].split("T")
        self.y, self.m, self.dy = d.split("-")
        self.h, self.mi = t.split(":")

    def manual_launch_info(self):
        # Variables in order of display on screen
        # T-0 time is formatted as "YYYY-MM-DDTHH:MMZ" where T and Z won't change. Input time should be in UTC.

        self.t0 = "2026-02-06T19:00Z"
        self.name = "Milan-Cortina"
        self.vehicle = "Games of the"
        self.pad = "XXV Winter"
        self.lc = "Olympiad"
        self.country = "Italy, Europe"

        d, t = self.t0[:-1].split("T")
        self.y, self.m, self.dy = d.split("-")
        self.h, self.mi = t.split(":")

    def countdown_loop(self, http_time=120, display_interval=0.2):
        # http_time (int) - default: 120 - the total time (in seconds) that the loop takes to reset and grab more data
        # display_interval (float) - default: 0.2 - interval (in seconds) to let the screen sleep each cycle

        if self.manual_setting:
            self.manual_launch_info()
        else:
            self.define_auto_vars()

        utc_launch_time = datetime(int(self.y), int(self.m), int(self.dy), int(self.h), int(self.mi))
        overall_utc_delta = timedelta(hours=self.utc_delta)
        full_launch_time = utc_launch_time + overall_utc_delta
        launch_date = str(full_launch_time).split(" ")[0]

        num_cycles = int(http_time / display_interval)

        for cycle in range(num_cycles):
            if self.button.value:
                print("Button pressed, acquiring the newest data")
                self.countdown_text_area.text = "LOADING"
                sleep(0.5)  # Protection against accidental button presses
                if self.manual_setting:
                    self.manual_setting = False
                    return
                else:
                    self.manual_setting = True
                    return

            current_time = datetime.now()
            countdown = full_launch_time - current_time

            # noinspection PyUnresolvedReferences
            total_seconds = int(countdown.total_seconds())
            days = total_seconds // 86400
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            if hours == 0:
                hour_logic = ""
            else:
                hour_logic = f"{hours}:"

            if hours >= 100:
                countdown_str = f"{days} Days"
            elif total_seconds <= 0:
                countdown_str = "00:00"
            else:
                countdown_str = f"{hour_logic}{minutes:02}:{seconds:02}"

            countdown_str = countdown_str.split('.')[0]

            self.main_row_1.text = f"{self.name}"
            self.main_row_2.text = f"{self.vehicle}"
            self.main_row_3.text = f"{self.pad}"
            self.main_row_4.text = f"{self.lc}"
            self.main_row_5.text = f"{self.country}"
            self.main_row_6.text = f"{launch_date}"
            self.main_row_7.text = f"Manual: {self.manual_setting}"

            self.countdown_text_area.text = f"{countdown_str}"

            self.counter += 1
            if self.counter == 1:
                print(f"Countdown active, manual flag initially set to {self.manual_setting}")
            elif self.counter / 10 == round(self.counter / 10):
                pass

            self.update_scrolls()

            sleep(display_interval)

    def run_loop(self, loop=True, setting=False, r=71, g=215, b=0):
        # The main setup + loop of this code.
        # loop (bool) - default: True - specifies if the user wants to actually run the loop or not
        # setting (bool) - default: False - the initial mode of the screen to possibly show the hardcoded time
        # r, g, b (ints) - defaults: 71, 215, 0 - hexcode of the accent of the display

        self.led_toggle(False)
        self.visuals((r, g, b))
        self.wifi_connect()
        self.manual_setting = setting
        self.utc_delta = self.get_utc_delta()

        if loop:
            while True:
                if self.manual_setting:
                    pass
                else:
                    self.get_launch_info()
                self.countdown_loop()
                self.manage_memory(verbose=False)
        else:
            return loop


if __name__ == "__main__":
    print("System on internal power")
    control = PicoControl()
    control.run_loop(loop=True, setting=True)
