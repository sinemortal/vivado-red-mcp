# Tcl quoting & list semantics for Vivado scripts

Upstream:
- UG894 (Vivado Tcl Scripting) — https://www.xilinx.com/content/dam/xilinx/support/documents/sw_manuals/xilinx2020_1/ug894-vivado-tcl-scripting.pdf
- Tcl 8.5 manual — https://www.tcl.tk/man/tcl/TclCmd/Tcl.htm

## Word splitting and quoting

Tcl tokenizes on whitespace UNLESS the words are grouped by:

| Form | Behaviour |
|---|---|
| `{word}` | Literal — **no** substitution of `$var`, `[cmd]`, or `\n`. Use for paths, code blocks, dict bodies. |
| `"word"` | Substituted — `$var` and `[cmd]` are expanded. |
| `\<space>` | Escape a space inside an unquoted word (rarely used). |

The Vivado convention: **paths and dicts go in braces**; computed strings go in
double quotes. Mixing them is the #1 source of "ERROR: invalid command name"
when a `$var` accidentally lands inside braces.

## `set_property -dict`

```tcl
# CORRECT — braces, key/value pairs separated by single spaces:
set_property -dict {CONFIG.PCW_USE_M_AXI_GP0 1 CONFIG.PCW_FCLK_CLK0_BUF TRUE} \
  [get_bd_cells processing_system7_0]

# WRONG — quotes would expand "TRUE" but here it's harmless; the bug is that
# Vivado expects -dict <list>, and an interpolated string still parses, just
# defeats the literal intent:
set_property -dict "CONFIG.X 1" [get_bd_cells ...]
```

Empty values: `CONFIG.FOO {}` — the inner braces become an empty Tcl list,
which Vivado treats as "unset".

## Paths with spaces

```tcl
# Wrap the path in braces:
open_project {C:/My Projects/foo.xpr}
add_files -fileset constrs_1 {C:/work/red pitaya/constraints.xdc}

# If the path is already in a Tcl variable, no extra braces needed:
set p {C:/work/red pitaya/constraints.xdc}
add_files -fileset constrs_1 $p
```

The MCP server's tools brace user-supplied paths automatically.

## Lists

Vivado `get_*` returns Tcl lists. To use them:

```tcl
foreach cell [get_bd_cells *] {
  puts "Cell: $cell"
}

set n [llength [get_cells -hierarchical *]]
puts "Total instances: $n"

set first [lindex [get_hw_devices] 0]
```

Slicing: `lrange $list 0 9` for the first 10 elements.

## Variable references

```tcl
set top "my_module"
puts $top                       ;# my_module
puts "Top is $top."             ;# substituted
puts {Top is $top.}             ;# LITERAL '$top'
puts "Result: [expr {1+2}]"     ;# 3
```

`{` blocks even `[brackets]`. To embed code that must execute, switch to
quotes or use `subst` explicitly.

## Common pitfalls in Vivado scripts

- Quoting a CONFIG value containing curly braces is a parser nightmare. Stick to numbers, identifiers, or quoted strings without braces.
- `get_property STATUS [get_runs synth_1]` returns a string like `"synth_design Complete!"`. Comparisons must use string matching, not numeric ops: `string match "*Complete*" $status`.
- Running `eval [list cmd args]` is rarely needed and usually a sign that path-quoting was wrong upstream.
- TCL booleans accept `1/0/true/false/yes/no/on/off` — all equivalent.
