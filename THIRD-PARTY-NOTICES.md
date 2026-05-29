# Third-Party Notices

This project bundles a small amount of third-party material. Each item below
keeps its own license; the project's own MIT license (see `LICENSE`) does not
override those terms.

## Red Pitaya board constraints (XDC)

These files are derived from the Red Pitaya reference design
(`RedPitaya/RedPitaya-FPGA`, `sdc/red_pitaya.xdc`, by Matej Oblak):

- `data/boards/red_pitaya_125_14_full.xdc`
- `data/boards/red_pitaya_125_14_leds_min.xdc`

Upstream: https://github.com/RedPitaya/RedPitaya-FPGA

Redistributed under the original 3-clause BSD license:

```
Copyright (c) 2014, Red Pitaya, d.o.o.  All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of Red Pitaya nor the names of its contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## Upstream project

This project is a fork of [`coreyhahn/vivado_mcp`](https://github.com/coreyhahn/vivado_mcp)
(MIT). The combined copyright notice is in `LICENSE`.

## Runtime dependencies

Installed from PyPI, **not** bundled in this repository — their licenses apply
to those packages, not to this project:

| Package    | License     |
|------------|-------------|
| `mcp`      | MIT         |
| `psutil`   | BSD-3-Clause|
| `paramiko` | LGPL-2.1    |
| `pexpect`  | ISC         |
| `pywinpty` | MIT         |
