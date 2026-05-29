# Vivado MCP — Red Pitaya quick-start usage

This guide shows how to go from a natural-language description to a working
`.bit.bin` file for the **Red Pitaya STEMlab 125-14** (Xilinx Zynq
`xc7z010clg400-1`) without touching the Vivado GUI.

You describe the project in chat, Claude writes the Verilog, calls
`create_redpitaya_project_rtl`, and hands back the absolute paths of
`<top>.bit` and `<top>.bit.bin`. You `scp` the `.bin` to the board and write
it to `/dev/xdevcfg`.

---

## Prerequisites (Linux host)

1. Vivado 2020.1 or newer, sourced in the shell that launches `vivado-mcp`:
   ```bash
   source /opt/Xilinx/2020.1/Vivado/settings64.sh
   ```
2. `pip install -e .` inside the cloned `vivado_mcp/` directory.
3. `.mcp.json` or `~/.claude/claude_desktop_config.json`:
   ```json
   { "mcpServers": { "vivado": { "command": "vivado-mcp" } } }
   ```

## Typical one-shot flow

In the chat, after Claude has a `start_session` running, it will:

1. Call `list_boards` / `get_board_info("red_pitaya_125_14")` to get the
   part number and bundled XDC paths.
2. Write your Verilog to a file (e.g. `/tmp/led_blinker.v`).
3. Call `create_redpitaya_project_rtl` with the file path and top module.
4. Return the `.bit` / `.bit.bin` paths from the composite's response.

You then load the bitstream on the board:

```bash
scp /tmp/rp_projects/led_blinker_1hz/led_blinker_1hz.runs/impl_1/led_blinker.bit.bin \
    root@rp-xx-xx-xx:/tmp/
ssh root@rp-xx-xx-xx 'cat /tmp/led_blinker.bit.bin > /dev/xdevcfg'
```

---

## Esempi di prompt (Italian)

### 1. LED blinker a 1 Hz

> Crea un LED blinker a 1 Hz per il Red Pitaya. Usa il clock ADC a 125 MHz e
> fai lampeggiare `led_o[0]`. Salva il progetto in `/tmp/rp_projects`.

Claude risponderà scrivendo un modulo `led_blinker` con un contatore a 26
bit, userà il variante XDC `leds_min`, e chiamerà una sola volta
`create_redpitaya_project_rtl`. Tempo atteso: 3–6 minuti.

File generato: `/tmp/rp_projects/led_blinker_1hz/led_blinker_1hz.runs/impl_1/led_blinker.bit.bin`

### 2. Contatore visibile sugli 8 LED

> Fai un contatore binario che mostri gli 8 bit più significativi di un
> contatore a 32 bit sugli 8 LED del Red Pitaya. Clock 125 MHz ADC.

Stesso flusso, ma il modulo guida tutti i bit di `led_o[7:0]`. `xdc_variant`
resta `leds_min` perché servono solo LED + clock.

### 3. GPIO passthrough su expansion connector

> Collega gli 8 pin `exp_p_io` in lettura a `led_o` in scrittura: quello
> che scrivo sulla E1 deve apparire sui LED.

Serve il pinout completo dell'expansion connector, quindi Claude userà
`xdc_variant="full"` e dichiarerà `exp_p_io[7:0]` come `input` e `led_o[7:0]`
come `output` nel top.

### 4. Lettura XADC

> Leggi il canale XADC `vinp_i[0]` a 10 kHz e scrivi i 4 MSB sui LED del Red
> Pitaya.

Serve il variante `full` (espone `vinp_i`/`vinn_i`). Claude istanzierà un
primitivo `XADC` con i parametri corretti o userà il blocco `XADC_WIZ`.

---

## Flusso a basso livello (se preferisci passo-passo)

Se non vuoi usare il composito, i primitivi sono tutti disponibili:

1. `start_session`
2. `get_board_info(board="red_pitaya_125_14")` → annota
   `xdc_variants.leds_min.absolute_path`
3. `create_project(name="my_proj", directory="/tmp/rp_projects")`
4. `add_sources(files=["/tmp/my_top.v"], set_top="my_top")`
5. `add_constraints(files=["<absolute_path del passo 2>"])`
6. `run_synthesis()`
7. `run_implementation()`
8. `generate_bitstream()`
9. `generate_cfgmem(bit_file=".../impl_1/my_top.bit")` → produce `.bit.bin`
10. `scp` + `/dev/xdevcfg` come sopra

## Quando qualcosa non funziona

- **Sintesi fallita:** chiama `get_synthesis_errors_parsed()` per avere la
  lista strutturata degli errori invece del log grezzo.
- **Timing non rispettato:** `get_timing_summary()` e `get_timing_paths()`.
- **Sessione bloccata:** `check_session_health(auto_recover=true)`.
- **Log completo:** `get_messages()` o `generate_full_report()` +
  `read_report_section()`.

Il progetto Vivado resta aperto dopo un fallimento — puoi ispezionarlo
con gli altri tool senza ricreare tutto.

## Template di riferimento

Un modulo Verilog minimale che blinker `led_o[0]` a ~1 Hz è incluso in
`data/templates/led_blinker_template.v`. Puoi partire da lì come esempio
canonico.

---

## Block Design (Zynq PS + AXI GPIO LED)

Per un design Zynq completo con PS7 + AXI GPIO che pilota gli 8 LED, il flusso
manuale è:

```text
start_session
create_project(name="ps7_leds", directory="/tmp/rp_projects")
create_block_design(name="system")
add_ip_to_bd(cell_name="processing_system7_0",
             vlnv="xilinx.com:ip:processing_system7:5.5")
apply_ps7_preset(cell="processing_system7_0", apply_board_preset=false)
# (Con board file Red Pitaya installato, apply_board_preset=true configura
# DDR + MIO + clocks automaticamente. Senza, le PCW_* vanno settate a mano.)

add_ip_to_bd(cell_name="axi_gpio_0", vlnv="xilinx.com:ip:axi_gpio:2.0",
             config={"CONFIG.C_GPIO_WIDTH": "8",
                     "CONFIG.C_ALL_OUTPUTS": "1"})
auto_connect_axi(master="/processing_system7_0/M_AXI_GP0",
                 slave="/axi_gpio_0/S_AXI")
assign_bd_address()
validate_block_design()
save_bd_design()
generate_bd_wrapper(bd_name="system", set_top=true)
load_board_xdc(board="red_pitaya_125_14", variant="leds_min")
run_synthesis()
run_implementation()
generate_bitstream()
generate_cfgmem(bit_file=".../impl_1/system_wrapper.bit")
```

Il PS7 espone `axi_gpio_0/gpio_io_o[7:0]` come output del wrapper — il
constraint XDC `leds_min` deve mappare quei pin a `led_o[*]`. Edit del XDC
o uso di `make_bd_pins_external` per portarli fuori dal block design.

## Hardware Manager (programmazione via JTAG, opzionale)

Solo se hai un cavo Xilinx JTAG attaccato al connettore JTAG della scheda:

```text
open_hw_manager
connect_hw_server(url="localhost:3121")
program_device(bit_file="/path/to/design.bit")
```

Per Red Pitaya l'approccio normale (`scp + /dev/xdevcfg`) resta più semplice.

## Documentazione embedded

Lista temi disponibili offline:

```text
list_vivado_docs
get_vivado_doc(topic="block_design")
get_vivado_doc(topic="ps7_zynq")
get_vivado_doc(topic="red_pitaya_125_14")
get_vivado_doc(topic="pitfalls_2020_1")
```

Ogni topic include link upstream alle UG ufficiali AMD per approfondire.
