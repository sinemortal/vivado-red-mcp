# Hardware Manager — JTAG programming

Upstream:
- UG908 (Programming and Debugging) — https://docs.amd.com/v/u/2020.1-English/ug908-vivado-programming-debugging

## When to use it

For Red Pitaya the default deploy path is `scp .bit.bin + /dev/xdevcfg` (no
cable needed). Use Hardware Manager when:

- A Xilinx-compatible JTAG cable is plugged into the board's JTAG header
  (Platform Cable USB II, Digilent HS3, or the on-board FTDI of dev kits like
  ZedBoard).
- You need to attach an Integrated Logic Analyzer (ILA) for live debug.
- You're programming a SPI flash (boot config) rather than the PCAP loader.

## Sequence

```tcl
open_hw_manager
connect_hw_server -url localhost:3121     ;# default hw_server listen port
open_hw_target                            ;# auto-detects connected target
current_hw_device [lindex [get_hw_devices] 0]
refresh_hw_device [current_hw_device]

set_property PROGRAM.FILE {/path/to/design.bit} [current_hw_device]
# Optional ILA probes file:
set_property PROBES.FILE {/path/to/debug_nets.ltx} [current_hw_device]

program_hw_devices [current_hw_device]
refresh_hw_device  [current_hw_device]
```

Cleanup:
```tcl
close_hw_target
disconnect_hw_server
close_hw_manager
```

## hw_server

`hw_server` is the standalone TCP daemon that talks to the physical cable.
It ships with Vivado at `<install>/bin/hw_server` (Linux) or `hw_server.bat`
(Windows). Start it once per host:

```bash
hw_server &           # listens on 3121
```

Then `connect_hw_server -url <hostname>:3121` from anywhere — including a
remote Vivado on a different machine.

## ILA capture (read-back)

After programming, with an ILA in the design:
```tcl
set ila [get_hw_ilas hw_ila_1]
set_property CONTROL.TRIGGER_POSITION 512 $ila
run_hw_ila $ila
wait_on_hw_ila $ila
display_hw_ila_data [upload_hw_ila_data $ila]
```

## Pitfalls

- `connect_hw_server` without a running hw_server times out silently. Start the daemon first.
- The JTAG cable driver (Digilent Adept or libusb-1.0) must be installed; on Linux you may need to source `<install>/data/xicom/cable_drivers/lin64/install_script/install_drivers/install_drivers`.
- Forgetting `open_hw_target` after `connect_hw_server` results in `current_hw_device` returning empty and the program step silently no-oping.
- On Zynq, programming the PL via JTAG bypasses the PS; the ARM cores stay where they were. Reset PS separately if needed.
