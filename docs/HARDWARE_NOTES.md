# Luckfox Pico Mini B hardware bring-up notes

## Wiring (ST7789 240x240)
CS   -> pin 6  (SPI0_CS0_M0)
CLK  -> pin 7  (SPI0_CLK_M0)
SDA  -> pin 8  (SPI0_MOSI_M0)  -- NOT pin 9 (MISO)!
RST  -> pin 12 (GPIO1_D0 / gpio56)
DC   -> pin 13 (GPIO1_D1 / gpio57)
BL   -> 3.3V direct

## Display driver: userspace, not fbtft
fbtft (kernel driver) never worked on 5.10 despite correct DT + wiring -
root cause never fully isolated (suspect: 5.10 gpiod reset polarity bug).
Abandoned in favor of neodct_displayd (src/neodct_displayd.c), which
drives the panel directly over /dev/spidev0.0 and mirrors a Linux
virtual framebuffer (vfb) to it. Proven working.

## Build gotchas
- SDK build MUST happen in Ubuntu 22.04 (distrobox). Native Arch hangs
  silently on the atbm wifi driver.
- neodct's own Buildroot tree builds fine natively on Arch.
- vfb is disabled by default even when CONFIG_FB_VIRTUAL=y and built-in;
  vfb_setup() stomps the enable flag at boot regardless of cmdline.
  Patched drivers/video/fbdev/vfb.c line ~399 to force-enable.
  See patches/luckfox-sdk/0001-vfb-force-enable.patch
- Real kernel cmdline comes from U-Boot env (.env.txt in SDK output),
  NOT from the DTS bootargs node. DTS bootargs are effectively ignored
  on this board.
- Flash rootfs only, without touching boot partition:
  sudo ./upgrade_tool di -rootfs rootfs.ubifs