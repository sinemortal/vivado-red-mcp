# Changelog

## 0.4.0 — 2026-10-28

Validated end-to-end on **Vivado 2026.1 (Windows 11)**: session, Red Pitaya RTL
and PS+PL builds, reports, behavioral and post-synthesis xsim, block design, and
the RedPitaya-FPGA `prj/Examples` tutorials. Led_blink and Knight_rider rebuilt
from scratch with MCP tools only produce bitstreams byte-identical to the
tutorials' own scripts.

### Fixed
- **MCP SDK**: pinned to 1.x (`mcp>=1.0,<2`). With 2.x the server failed to start
  (`'Server' object has no attribute 'list_tools'`).
- **xsim under Claude Code on Windows**: Vivado no longer inherits
  `NoDefaultCurrentDirectoryInExePath` (set by Claude Code for its children).
  With it, xsim could not spawn its generated `compile.bat` ("Spawn failed: file
  not found"), so simulation never worked from Claude Code.
- **Startup errors**: if Vivado exits during startup (e.g. missing license),
  `start_session` fails in seconds and returns Vivado's own message, instead of
  `Child stdin closed` after a 120 s timeout.
- **Multi-line `run_tcl`**: the Windows console dropped the newlines
  (`set x 1\nset y 2` arrived as `set x 1set y 2`). Scripts are now sent as one
  line that decodes and evaluates the exact text; Tcl errors set `success=false`.
- **`get_timing_summary`**: parses the Design Timing Summary table (it always
  returned empty values before); `NA` columns stay empty; `met` means every
  reported slack is >= 0.
- **`get_utilization`**: handles the `Prohibited` column of newer releases and
  `<0.01` values; the 2020.1 layout is still parsed.
- **Reports right after a build** (timing, utilization, clocks, power, DRC, full
  reports) failed silently with "No open design". They now open the latest
  completed run (impl_1, else synth_1) and return the error text otherwise.
- **`generate_bitstream`**: default timeout 3600 s (was 300 s), verified run
  status, returns the `.bit` path.
- **`get_synthesis_errors_parsed`**: always returned 0 errors because it read
  the session messages, which never hold `launch_runs` errors. It now parses the
  log of the requested run and of every failed run (e.g. out-of-context IP runs).
- **`launch_simulation`**: uses the documented mode values (`behavioral`,
  `post-synthesis` / `post-implementation` + `-type functional|timing`); recent
  Vivado rejects the abbreviations.
- **Bundled `red_pitaya_125_14_full.xdc`**: 6 wrong pins compared with upstream
  `sdc/red_pitaya.xdc` and the tutorials — ADC channel A MSB
  (`adc_dat_i[0][13]` V17 → V16) and `dac_dat_o[8..12]`.
- **PS+PL flow** (`rp_*`): supports the current RedPitaya-FPGA layout
  (`red_pitaya_vivado_Z10.tcl` + `DEV_MODE`, `ip/system.tcl`, `prj/<name>/build`)
  as well as the legacy one. The workspace copy (never the source checkout) is
  patched so exported block-design/IP scripts run on the installed Vivado and
  the git-hash stamp works without git.
- Repository links now point to `sinemortal/vivado-mcp`.

### Added
- `create_bd_port` — scalar, vector and interface block-design ports.
- `add_module_to_bd` — RTL module-reference cells with parameters.
- `configure_bd_cell` — `CONFIG.*` on an existing cell (e.g. PS7 preset import).
- `set_run_strategy` — synthesis/implementation run strategy.
- `create_redpitaya_project_rtl` and `rp_build_project` return parsed
  `timing_summary` (and `utilization` for RTL) next to the raw text.

### Docs
- README rewritten: tested versions, licensing for Vivado 2025.x/2026.x,
  installation and Claude Code registration (`claude mcp add`), troubleshooting.
- PS+PL flow doc covers both RedPitaya-FPGA layouts and the workspace patches.

## 0.3.1

- Output-capture fallback, host status cleanup, doc topic validation.

## 0.3.0

- `rp_fetch_repo` and startup auto-fetch of RedPitaya-FPGA.
