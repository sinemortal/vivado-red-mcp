# IP catalog & customization

Upstream:
- UG896 (Designing with IP) — https://docs.amd.com/v/u/2020.1-English/ug896-vivado-ip
- UG835 §create_ip / §generate_target / §synth_ip
- UG994 (IP Integrator)

## Catalog vs. IPI

- **IP catalog** (`create_ip ...`) creates a *standalone* IP instance with its own
  `.xci` and (optionally) its own OOC synth run. Used from plain RTL when you
  want a clk_wiz or FIFO without a block design.
- **IP Integrator** (`create_bd_cell ...`) wraps the same IPs into a graphical
  block design. The `.xci` files for IPI-managed cells live inside the BD's
  output tree.

You can mix both — a top-level RTL can instantiate a clk_wiz from the catalog
AND a block design wrapper.

## Catalog flow

```tcl
create_ip -name clk_wiz -vendor xilinx.com -library ip \
  -version 6.0 -module_name clk_125_to_200

set_property -dict {
  CONFIG.PRIM_IN_FREQ 125.000
  CONFIG.CLKOUT1_REQUESTED_OUT_FREQ 200.000
  CONFIG.USE_LOCKED true
  CONFIG.USE_RESET false
} [get_ips clk_125_to_200]

generate_target {synthesis simulation} [get_files clk_125_to_200.xci]
synth_ip [get_ips clk_125_to_200]            ;# optional OOC synth
```

## CONFIG.* discovery

To list every property of an IP:
```tcl
report_property [get_ips clk_125_to_200]
```

To find what an IP supports BEFORE creating it:
```tcl
get_ipdefs -filter {NAME =~ "clk_wiz"} -all
# Returns version-specific defs; pick the latest:
set ipdef [lindex [get_ipdefs -filter {NAME =~ "clk_wiz"} -all] end]
report_property $ipdef
```

## Upgrade vs lock

Vivado warns when an IP is older than the catalog. Three options:

```tcl
upgrade_ip [get_ips clk_125_to_200]              ;# upgrade single IP
upgrade_ip [get_ips]                              ;# upgrade all
report_ip_status                                  ;# audit current state
```

Locking an old IP (compliance/regression freeze):
```tcl
set_property IS_LOCKED TRUE [get_files clk_125_to_200.xci]
```

## OOC synthesis runs

By default `GENERATE_SYNTH_CHECKPOINT=TRUE` on every IP — Vivado creates a
synth run `synth_<ip>_1` per IP. To force the IP into the global synth scope:

```tcl
set_property GENERATE_SYNTH_CHECKPOINT FALSE [get_files myfifo.xci]
```

This trades incremental-build cache for slightly better global QoR.

## Pitfalls

- Forgetting `generate_target` leaves the IP unsynthesized; `synth_design` will report `[Synth 8-439] module 'clk_125_to_200' not found`.
- `synth_ip` is OOC — it does NOT add the IP into the project's synth_1 run. Use it to pre-warm the cache; `synth_design` at the top level still needs to integrate.
- `CONFIG.PRIM_IN_FREQ` is a string, not a number — quotes are not required but braces ARE if the value contains a space.
- Upgrading an IP can introduce new CONFIG keys with non-default values. Always re-run `validate_bd_design` after `upgrade_ip` inside an IPI flow.
