# Compile RP2040 with slow XTAL

[Firmware download](ports/rp2/build-RPI_PICO/firmware.uf2)

## Preparation

```bash
sudo apt update && \
    sudo apt install -y gcc-arm-none-eabi \
    build-essential \
    git \
    python3 \
    cmake

(cd ports/rp2 && make submodules)
```

## Patch

```bash
# Banner
sed -i 's/Raspberry Pi Pico/Raspberry Pi Pico (slow XTAL, 16MBytes Flash)/g' ports/rp2/boards/RPI_PICO/mpconfigboard.h
sed -i 's/(1408 \* 1024)/(15 \* 1024 \* 1024)/g' ports/rp2/boards/RPI_PICO/mpconfigboard.h
# 16 MBytes Flash
sed -i 's/PICO_FLASH_SIZE_BYTES (2 /PICO_FLASH_SIZE_BYTES (16 /g' lib/pico-sdk/src/boards/include/boards/pico.h
# Slow Xtal
sed -i 's/#define PICO_XOSC_STARTUP_DELAY_MULTIPLIER 1/#define PICO_XOSC_STARTUP_DELAY_MULTIPLIER 64/g' lib/pico-sdk/src/rp2_common/hardware_xosc/include/hardware/xosc.h
```

## Compile
```bash
make -C mpy-cross/ -j 16
make -C ports/rp2 BOARD=RPI_PICO clean
make -C ports/rp2 BOARD=RPI_PICO submodules
make -C ports/rp2 BOARD=RPI_PICO -j 16

ls -la ./ports/rp2/build-RPI_PICO/firmware.uf2
-rw-rw-rw- 1 codespace codespace 649728 Feb 24 18:14 ./ports/rp2/build-RPI_PICO/firmware.uf2
```

## Commit

```bash
git add -f ./ports/rp2/build-RPI_PICO/firmware.uf2
```

# Is there another micropython port which would fit our board?

```bash
grep -r '#define PICO_FLASH_SIZE_BYTES (16 ' ports/rp2/
ports/rp2/boards/WEACTSTUDIO/weactstudio_16MiB.h:#define PICO_FLASH_SIZE_BYTES (16 * 1024 * 1024)
ports/rp2/boards/POLOLU_ZUMO_2040_ROBOT/pololu_zumo_2040_robot.h:#define PICO_FLASH_SIZE_BYTES (16 * 1024 * 1024)
```

```bash
grep -r '#define PICO_XOSC_STARTUP_DELAY_MULTIPLIER 64' ports/rp2/
ports/rp2/boards/NULLBITS_BIT_C_PRO/nullbits_bit_c_pro.h
```

==> There no reasonalbe port for us...
