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
sed -i 's/Raspberry Pi Pico/Raspberry Pi Pico (slow XTAL)/g' ports/rp2/boards/RPI_PICO/mpconfigboard.h
# Generic FLASH
# sed -i 's/PICO_BOOT_STAGE2_CHOOSE_W25Q080/PICO_BOOT_STAGE2_CHOOSE_GENERIC_03H/g' lib/pico-sdk/src/boards/include/boards/pico.h
sed -i 's/#define PICO_XOSC_STARTUP_DELAY_MULTIPLIER 1/#define PICO_XOSC_STARTUP_DELAY_MULTIPLIER 64/g' lib/pico-sdk/src/rp2_common/hardware_xosc/include/hardware/xosc.h
# 16 MBytes Flash
sed -i 's/(2 \* 1024 \* 1024)/(16 * 1024 * 1024)/g' lib/pico-sdk/src/boards/include/boards/pico.h
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
