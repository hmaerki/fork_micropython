# Target wiring for general esp32 board.
#
# Connect:
# - GPIO4 to GPIO5
# - GPIO12 to GPIO13

import sys

uart_loopback_args = (1,)
uart_loopback_kwargs = {"tx": 4, "rx": 5}

if any(m in sys.implementation._machine for m in ("ESP32-C", "ESP32-H2")):
    spi_standalone_args_list = [(1,)]
else:
    spi_standalone_args_list = [(1,), (2,)]

pwm_loopback_pins = [(4, 5)]


encoder_loopback_id = 0
if ("ESP32-H2" in sys.implementation._machine) or ("ESP32-C5" in sys.implementation._machine) or ("ESP32-C6" in sys.implementation._machine):
    encoder_loopback_out_pins = (4, 10)
    encoder_loopback_in_pins = (5, 11)
else:
    encoder_loopback_out_pins = (4, 12)
    encoder_loopback_in_pins = (5, 13)

i2c_target_args = (0,)
if sys.implementation._build == "ESP32_GENERIC_C5":
    # ESP32-C5-DevKitC-1 v1.2: No pin 22!
    i2c_controller_kwargs = {"scl": 10, "sda": 12}
    i2c_target_kwargs = {"scl": 11, "sda": 24}
if sys.implementation._build == "ESP32_GENERIC_C6":
    # ESP32-C6-DevKitC-1 v1.2: Pin 12,13 used by XTAL!  
    i2c_controller_kwargs = {"scl": 10, "sda": 22}
    i2c_target_kwargs = {"scl": 11, "sda": 23}
elif sys.implementation._build in ("ESP32_GENERIC_H2", "ESP32_GENERIC_C2", "ESP32_GENERIC_S2"):
    i2c_controller_kwargs = {"scl": 10, "sda": 12}
    i2c_target_kwargs = {"scl": 11, "sda": 22}
else:
    i2c_controller_kwargs = {"scl": 5, "sda": 6}
    i2c_target_kwargs = {"scl": 9, "sda": 8}
