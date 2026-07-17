# SIM7600G Modem Bring-Up (0.3.0a)

How NeoDCT talks to the SIM7600G-H on T-Mobile, from raw AT pokes to live
signal bars on the home screen. No ModemManager, no libqmi, no PPP — the
whole stack is BusyBox + the kernel's `option` and `qmi_wwan` drivers +
~400 lines of Python.

## The stack

| Layer | Piece | Job |
|-------|-------|-----|
| kernel | `option` driver | `1e0e:9001` is in its device table (SIM7100/7600 entry) → auto-binds, creates `/dev/ttyUSB0-4` |
| kernel | `qmi_wwan` + `usb_wdm` | `wwan0` network interface at the stock PID, no mode-switching |
| shell | `/NeoDCT/System/engineering/tools/atcmd` | one scriptable AT command per call, lock-safe |
| boot | `/etc/init.d/S45modem` | backgrounded auto-connect: SIM → register → `AT$QCRMCALL` → SLAAC |
| UI | `System/core/ModemService` | owns the AT port from Python; CSQ → home-screen bars, call control, URC events |

Port map at the stock PID `1e0e:9001`:

| Node | Interface | Purpose |
|------|-----------|---------|
| `/dev/ttyUSB0` | 0 | Qualcomm DIAG (binary — leave it alone) |
| `/dev/ttyUSB1` | 1 | GPS NMEA stream |
| `/dev/ttyUSB2` | 2 | **AT commands** ← everything here uses this |
| `/dev/ttyUSB3` | 3 | AT / PPP modem port (spare) |
| `/dev/ttyUSB4` | 4 | **call audio PCM** (16 kHz mono S16_LE after `AT+CPCMREG=1`) |

## QEMU passthrough recap

```
-device qemu-xhci,id=xhci
-device usb-host,bus=xhci.0,vendorid=0x1e0e,productid=0x9001
```

* `chmod 666 /dev/bus/usb/BBB/DDD` on the host (avoids running QEMU as
  root, which breaks PulseAudio).
* **Stop ModemManager on the host first** (`systemctl stop ModemManager`):
  it grabs the AT ports the moment the modem enumerates and QEMU may
  detach the device mid-conversation, leaving the firmware confused.
* **Never `AT+CUSBPIDSWITCH`** while using QEMU passthrough: the modem
  re-enumerates with a new product ID and the `productid=0x9001` filter
  stops matching, so the modem vanishes from the guest. (Also the reason
  we use `$QCRMCALL` instead of RNDIS mode.)
* Hardware note: until the blown CapXon cap is bodged (470–1000 µF ≥6.3 V
  across 5 V/GND), expect possible brownout reboots during LTE TX bursts.
  A mid-session reboot looks like all `ttyUSB*` nodes vanishing and
  re-enumerating — `dmesg` will show the disconnect.

## Stage 1 — terminal proof of concept

`atcmd` ships in the image at `/NeoDCT/System/engineering/tools/atcmd`.
Sanity checks first:

```sh
alias at='/NeoDCT/System/engineering/tools/atcmd'
at AT              # -> OK              (modem alive)
at ATI             # -> SIM7600 model info
at AT+CPIN?        # -> +CPIN: READY    (SIM detected/unlocked)
at AT+CSQ          # -> +CSQ: 20,99     (rssi 0-31; 99,99 = no signal yet)
at AT+CEREG?       # -> +CEREG: 0,1     (…,1 home / …,5 roaming = registered)
at AT+COPS?        # -> +COPS: 0,0,"T-Mobile",7
```

Then the data call (T-Mobile is IPv6-only with NAT64/DNS64):

```sh
at 'AT+CGDCONT=1,"IPV6","fast.t-mobile.com"'
at -t 15 'AT$QCRMCALL=1,1'          # firmware starts the RmNet call
ip link set wwan0 up
sysctl -w net.ipv6.conf.wwan0.accept_ra=2
sleep 5                              # SLAAC: address arrives via RA
ip -6 addr show dev wwan0            # want a "scope global" inet6 here
ping -6 -c 3 2606:4700:4700::1111    # packets over a REAL TOWER
```

DNS for name resolution (Google DNS64, synthesizes AAAA for v4-only hosts):

```sh
echo 'nameserver 2001:4860:4860::6464' >> /etc/resolv.conf
```

Useful extras: `AT+CGPADDR=1` (modem's view of the address),
`AT+CGCONTRDP=1` (address + T-Mobile's own DNS servers),
`AT$QCRMCALL?` (call state), `AT$QCRMCALL=0,1` (tear down).

## Stage 2 — automatic connection at boot

`/etc/init.d/S45modem` runs the whole Stage-1 sequence in the background
at every boot (boot itself never blocks): waits for the AT port, checks
the SIM, defines the context, waits up to 90 s for LTE registration,
starts `$QCRMCALL`, brings up `wwan0`, waits for SLAAC, appends DNS64
nameservers, then ping-tests.

* Watch it work: `tail -f /tmp/modem-boot.log`
* One-word answer: `cat /tmp/modem.status` → `up:wwan0` / `failed: …`
* Re-run by hand: `/etc/init.d/S45modem restart`

Overrides live in `/etc/default/modem` (plain sh, all optional):

```sh
MODEM_APN="fast.t-mobile.com"
MODEM_PDPTYPE="IPV6"        # or IP / IPV4V6
MODEM_PORT="/dev/ttyUSB2"
MODEM_RAW_IP="auto"         # set "y" if SLAAC times out (see below)
```

## Stage 3 — the software (ModemService)

`System/core/ModemService` now drives the real modem (same
probe-or-simulate pattern as BatteryService):

* **Live signal bars**: polls `AT+CSQ` every 5 s; the home-screen `sig`
  icon_set renders 0–4 real bars (not registered → 0 bars). In QEMU
  without passthrough it stays on the layout's `sim_val`.
* **Port auto-probe**: prefers USB interface 2, then 3 (read from sysfs),
  confirms with `AT`→`OK`; re-probes every 10 s if the modem is missing,
  so passthrough/hotplug attach after boot is adopted automatically.
* **Live carrier line**: the home screen's "No Service" text becomes the
  real operator name ("Tello" / "T-Mobile", short-format `AT+COPS=3,1`)
  once registered; it falls back to "No Service" whenever registration
  drops.
* **Calls are LIVE and FULL-DUPLEX**: `system.modem.allow_calls`
  defaults ON (OFF restores the pretend flow). `dial()` sends `ATD`,
  then immediately `AT+CPCMREG=1`, then runs two alsa-utils pipes on the
  bidirectional PCM port: `aplay -t raw -f S16_LE -r 16000 -c 1
  /dev/ttyUSBn` (downlink → speaker) and `arecord … -D <mic> /dev/ttyUSBn`
  (USB sound card mic → uplink). Mic device:
  `system.hw.modem_mic_device` ("default"; `plughw:N,0` to pin;
  OFF = listen-only; three arecord failures auto-degrade to listen-only
  — check `arecord -l` and capture levels with `amixer`). Teardown
  (End key, `NO CARRIER`, `VOICE CALL: END`) kills both pipes and sends
  `AT+CPCMREG=0`; the call screen exits by itself on remote hangup.
  Typing a number plays fake DTMF beeps (`System/tones/dtmf/`). Test
  line: 1-800-444-4444 (MCI readback — it reads your voice channel back,
  so hearing your own mic echo confirms full duplex!). QEMU note: if
  `arecord -l` in the guest is empty, QEMU's usb-audio is playback-only
  on your build — use `-device virtio-sound-pci,audiodev=audio0`
  instead/alongside (kernel already has `CONFIG_SND_VIRTIO=y`).
  Bench note: LTE TX during a call is the worst case for the missing
  capacitor — if the modem vanishes mid-call, that's the brownout.
* **Coexistence**: every port transaction takes the advisory lock
  `/tmp/neodct-modem.lock`, shared with `atcmd` and `S45modem` — you can
  poke AT commands from the serial console while the UI runs.
* **Sim hooks** (QEMU, no modem): `echo 23 > /tmp/neodct_sim_csq` drives
  the bars; `echo 5551234 > /tmp/neodct_sim_ring` fakes an incoming call
  (`rm` it to "hang up"); `echo Tello > /tmp/neodct_sim_operator` fakes
  the carrier line; dialing auto-"connects" after 2 s.
* **SMS sending is LIVE** (the first real telephony): Messages → Write
  Message → Options → Send prompts for a number (arrow keys open the
  PhoneBook contact picker) and sends via `ModemService.send_sms()` —
  text-mode `AT+CMGS` with special handling for the newline-less `>`
  prompt.
* **SMS receiving is LIVE, 3310-style** (NotifyService): `AT+CNMI`
  pushes `+CMTI` the instant a message lands → fetched with `AT+CMGR`,
  deleted from the SIM, stored in the inbox DB. The original Nokia tone
  beeps immediately; the home screen shows "N message(s) received" with
  the **Read** softkey (C dismisses) and a flashing envelope while
  unread mail exists. A boot sweep (`AT+CMGL="REC UNREAD"`) imports
  messages that arrived while the phone was off. QEMU sim hook:
  `echo '5551234|hey' > /tmp/neodct_sim_sms`.
* **Incoming calls ring and interrupt apps**: `RING`/`+CLIP` →
  `IncomingCall` (a `BaseException`, like `KeyboardInterrupt`) raised
  from `read_keypress` unwinds whatever app is running (their `finally`
  blocks release ALSA), then the 3310-style screen shows the caller with
  a flashing "calling", **Answer** softkey and **C** to decline. The
  ringtone is `system.audio.ringtone`, looped in-process via miniaudio.
  QEMU sim hook: `echo 16165551234 > /tmp/neodct_sim_ring` rings once
  per write/touch; `rm` it to make the caller give up.
* **Modem engineering app** (menu id 9005): RADIO / SIM / DATA status
  pages, softkey walks Next→Next→Exit. Shows operator, CEREG, CSQ+dBm,
  CPIN, phone number, IMEI, ICCID, IMSI, firmware, S45modem status, wwan
  interface, IPv6, APN and DNS — troubleshooting without a serial
  console. In Simulation Mode it lists which ttyUSB nodes exist instead
  of bailing out.

## Troubleshooting

| Symptom | Meaning / fix |
|---------|---------------|
| no `/dev/ttyUSB*` | `lsusb` shows `1e0e:9001`? If yes: kernel missing `option` driver (needs the 0.3.0a image). If no: passthrough/cable/power. |
| `+CSQ: 99,99` forever | No RF: antenna, or modem brownout-rebooted (cap bodge). |
| `+CEREG: 0,2` stuck | Searching. Check antenna + `AT+CPIN?`; give it 1–2 min. |
| `+CEREG: 0,3` | Registration denied — APN/SIM plan issue usually. |
| `$QCRMCALL` OK but no SLAAC address | Toggle framing: `MODEM_RAW_IP=y` in `/etc/default/modem` (or manually: `ip link set wwan0 down; echo Y > /sys/class/net/wwan0/qmi/raw_ip; ip link set wwan0 up`). |
| ping works, names don't | resolv.conf lacks a DNS64 server (Stage 1 step). |
| `atcmd: modem port busy` | S45modem mid-registration or UI polling — it clears in seconds. |
| everything vanished mid-test | Modem rebooted (power) or host re-grabbed it (ModemManager). |
