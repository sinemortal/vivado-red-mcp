# Synthesis strategies — Vivado 2020.1

Upstream:
- UG901 (Vivado Synthesis) — https://docs.amd.com/v/u/2020.1-English/ug901-vivado-synthesis
- UG949 (UltraFast Methodology)

## Built-in strategies (`synth_design -directive`)

| Directive | Tradeoff |
|---|---|
| `Default` | Balanced area/runtime |
| `RuntimeOptimized` | Fastest synth, weakest QoR — for sandbox builds |
| `AreaOptimized_high/medium` | Smallest area, longest runtime |
| `AreaMapLargeShiftRegToBRAM` | Maps shift regs to BRAM (good for FIR designs) |
| `AlternateRoutability` | More routing flexibility, area cost |
| `PerformanceOptimized` | Aggressive replication for fanout |
| `FewerCarryChains` | Replaces CARRY4 with LUTs for placement freedom |

Applied per-run on a project:

```tcl
set_property STRATEGY {Vivado Synthesis Defaults} [get_runs synth_1]
set_property STEPS.SYNTH_DESIGN.ARGS.DIRECTIVE PerformanceOptimized [get_runs synth_1]
```

## Flag-level tuning

The MORE OPTIONS property lets you stack flags:

```tcl
set_property -name {STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS} \
  -value {-flatten_hierarchy none -bufg 16 -keep_equivalent_registers} \
  [get_runs synth_1]
```

Key flags:

- `-flatten_hierarchy none|rebuilt|full` — `none` preserves user hierarchy (best for reports, slightly worse QoR). Default `rebuilt` is the right balance.
- `-bufg <N>` — limit number of BUFG primitives. Red Pitaya canonical scripts pin this to 16 (the Zynq 7010 has 32 BUFGs).
- `-keep_equivalent_registers` — disables register replication during synth (helps reproducible builds).
- `-gated_clock_conversion off|auto|on` — clock gating cell handling.
- `-fsm_extraction off|one_hot|sequential|johnson|auto` — FSM encoding.
- `-resource_sharing off|auto|on` — share arithmetic resources.
- `-no_lc` — disable LUT combining.

## Per-module attributes

In RTL:

```verilog
(* dont_touch = "yes" *) reg [31:0] debug_probe;
(* keep_hierarchy = "yes" *) module my_critical_path (...);
(* mark_debug = "true" *) wire [7:0] suspicious_bus;
```

VHDL:

```vhdl
attribute dont_touch : string;
attribute dont_touch of debug_probe : signal is "yes";
```

## OOC vs Global synthesis

Vivado defaults IPs to *out-of-context* (OOC) synthesis — each IP gets its own
`synth_<ip>_1` run, results cached. Pros: incremental builds. Cons: black-boxed
during top synth (less cross-IP optimization).

To force global:
```tcl
set_property GENERATE_SYNTH_CHECKPOINT FALSE [get_files <module>.xci]
```

## Pitfalls

- `-flatten_hierarchy full` makes timing reports unreadable (no module paths). Use only for last-mile QoR experiments.
- `dont_touch` and `keep_hierarchy` propagate to opt_design — they prevent optimization across boundaries even later. Apply surgically.
- `STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS` is a single STRING property — every change overwrites the previous value. Concatenate, don't repeat the call.
- Changing strategies invalidates the synth run; `reset_run synth_1` is required.
