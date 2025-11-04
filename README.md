# PicoTimers
![GitHub Release](https://img.shields.io/github/v/release/gsl4295/PicoTimers?include_prereleases&sort=date&display_name=tag)
![GitHub commit activity](https://img.shields.io/github/commit-activity/t/gsl4295/PicoTimers)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/gsl4295/PicoTimers)<br>
A CircuitPython-based microcontroller dedicated to showing a live countdown to the next orbital rocket launch.

### Hardware
- The pin diagram for my screen specifically is located in `/info/pin-info.md`
- A top-down view of my setup is in `/info/pico-top-down-view.jpg`
- I used a [Raspberry Pi WH](https://www.amazon.com/Raspberry-Pi-RP-PICO-WH-Pico-WH/dp/B0C58X9Q77) (**W**ifi enabled, **H**eaders attached)
- The exact screen I used is a 1.8" 128x160 SPI TFT display. Find it [here on Amazon](https://a.co/d/0OCU4uG).

### Installation & Setup
- This is coded in CircuitPython-9.X. Download the latest version [here](https://circuitpython.org/board/raspberry_pi_pico_w/).
- I use Thonny for my microcontrollers, but I'm sure there are alternatives.
  - In Thonny you can download CircuitPython onto the Pico easily through the Interpreter tab of the Options menu.
  - Just make sure to press the 'bootsel' button on the Pico the first time you plug it in.
- It also uses adafruit's [extra libraries package](https://circuitpython.org/libraries). Make sure to grab a version that is compatible with 9.X '.mpy' file types (it seems like 10.X will also work).
  - From this package, it is necessary to copy the following files or folders over to your pico's /lib directory.
    - adafruit_display_text
    - adafruit_datetime
    - adafruit_requests
    - adafruit_st7735r
    - adafruit_connection_manager
    - adafruit_ticks
- Use environment variables for internet connectivity through CircuitPython's built-in `settings.toml` file. 
  - Set "WIFI" and "PASS" to strings of your SSID and password. The whole file should look like this:<br>
```toml
WIFI = "placeholder"
PASS = "placeholder"
```

### launch.py
- *Manual countdown data*
  - Toggles the screen between the next orbital rocket and a hardcoded date & time input from the user.
  - This feature can be toggled with a button. More details are located in `pin-info.md`
- *Functional GUI*
  - One of the main goals I had with this project was to make clean, modular graphics on the display.
  - The `adafruit_display_text` library is simply amazing for this purpose, as you'll especially see from the scrolling text.
- *[RocketLaunch.Live](https://rocketlaunch.live) integration*
  - This code partially relies on data from [the rocketlaunch.live API](https://rocketlaunch.live/api).
  - It's like the Wikipedia of launch tracking, so anyone can contribute.
  - Plus, more contributions will only make this code more reliable!
- *Automatic DST Conversion*
  - It calls [timeapi.io](https://timeapi.io) in order to update the daylight savings time calculations at startup only.

### clock.py
- A simple digital clock that displays the current time and date on the screen.
- Rather than using timeapi.io, this code uses the built-in RTC (real-time clock).
- Right now it's just meant for desk use, so it's ultra-simple.

### Future Improvements
- Main "picker" script to choose between launch.py and clock.py at startup.
- More time-related subtitles in clock.py.
- Try to use RTC for launch.py to avoid API calls for time.

Thanks for reading :)