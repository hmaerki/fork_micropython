# requires: target-wiring

import re
import sys

print()
print("CONNECTED BOARD")
print()
print(f"{sys.implementation._machine=}")
print(f"{sys.implementation._build=}")

print()
print("REQUIRED CONNECTIONS")
print()


def print_connections_uart():
    try:
        from target_wiring import uart_loopback_args, uart_loopback_kwargs
        from machine import UART
    except ImportError:
        print("uart-loopback-tests not supported!")
        return

    uart = UART(*uart_loopback_args, **uart_loopback_kwargs)
    uart_s = repr(uart)
    tx = int(re.search(r"tx=(-?\d+)", uart_s).group(1))
    rx = int(re.search(r"rx=(-?\d+)", uart_s).group(1))
    print("uart-loopback-tests:")
    print(f"  Pin {tx} <-> Pin {rx}  (tx <-> rx)")
    print()


print_connections_uart()


def print_connections_i2c():
    try:
        from target_wiring import (
            i2c_loopback_controller_kwargs,
            i2c_loopback_target_args,
            i2c_loopback_target_kwargs,
        )
        from machine import Pin, SoftI2C, I2CTarget
    except ImportError:
        print("i2c-target-tests not supported!")
        return

    i2c_target = I2CTarget(*i2c_loopback_target_args, **i2c_loopback_target_kwargs, addr=67)
    s = repr(i2c_target)
    target_scl = int(re.search(r"scl=(-?\d+)", s).group(1))
    target_sda = int(re.search(r"sda=(-?\d+)", s).group(1))
    print("i2c-target-tests:")
    print(
        f"  Pin {i2c_loopback_controller_kwargs['scl']} <-> Pin {target_scl}  (controller-scl <-> (target-scl)"
    )
    print(
        f"  Pin {i2c_loopback_controller_kwargs['sda']} <-> Pin {target_sda}  (controller-sda <-> (target-sda)"
    )
    print()


print_connections_i2c()


def print_connections_encoder():
    try:
        from target_wiring import (
            encoder_loopback_id,
            encoder_loopback_out_pins,
            encoder_loopback_in_pins,
        )
    except ImportError:
        print("encoder-loopback-tests not supported!")
        return

    print("encoder-loopback-tests:")
    for i in (0, 1):
        print(
            f"  Pin {encoder_loopback_out_pins[i]} <-> Pin {encoder_loopback_in_pins[i]}  ({i}: out <-> in)"
        )
    print()


print_connections_encoder()


def print_connections_pwm():
    try:
        from target_wiring import pwm_loopback_pins
    except ImportError:
        print("pwm-loopback-tests not supported!")
        return

    print("pwm-loopback-tests:")
    for pins in pwm_loopback_pins:
        print(f"  Pin {pins[0]} <-> Pin {pins[1]}  (pwm <-> pulse)")
    print()


print_connections_pwm()
