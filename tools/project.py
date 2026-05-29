"""Project management — open/close/info/create + sources/constraints + boards."""

from __future__ import annotations

from pathlib import Path

from mcp.types import Tool

from ..boards import DEFAULT_PART, list_bundled_boards, load_board_info
from ._common import err, require_args, require_project_open

TOOLS = [
    Tool(
        name="open_project",
        description="Open an existing Vivado project (.xpr file).",
        inputSchema={
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "Path to .xpr project file"}
            },
            "required": ["project_path"],
        },
    ),
    Tool(
        name="close_project",
        description="Close the currently open project.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_project_info",
        description="Get name, part, target language, directory of the open project.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="create_project",
        description=(
            "Create a new Vivado project on disk in project mode. Defaults to the "
            "Red Pitaya STEMlab 125-14 part (xc7z010clg400-1). Call add_sources / "
            "add_constraints next, then run_synthesis."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name"},
                "directory": {
                    "type": "string",
                    "description": "Parent directory; project created at <directory>/<name>",
                },
                "part": {
                    "type": "string",
                    "description": f"Xilinx part number (default: {DEFAULT_PART})",
                },
                "force": {"type": "boolean", "description": "Overwrite existing project (default: true)"},
                "target_language": {
                    "type": "string",
                    "description": "Verilog or VHDL (default: Verilog)",
                },
            },
            "required": ["name", "directory"],
        },
    ),
    Tool(
        name="add_sources",
        description=(
            "Add HDL source files (.v/.sv/.vhd) to the current project. Optionally "
            "sets the top module and updates compile order."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Absolute paths to HDL source files",
                },
                "fileset": {"type": "string", "description": "Target fileset (default: sources_1)"},
                "set_top": {
                    "type": "string",
                    "description": "If given, set this module as project top after adding files",
                },
            },
            "required": ["files"],
        },
    ),
    Tool(
        name="add_constraints",
        description="Add XDC constraint files to the current project.",
        inputSchema={
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Absolute paths to .xdc files",
                },
                "fileset": {"type": "string", "description": "Target fileset (default: constrs_1)"},
            },
            "required": ["files"],
        },
    ),
    Tool(
        name="list_boards",
        description="List boards with bundled XDC + metadata. No Vivado session required.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_board_info",
        description=(
            "Get bundled metadata for a board: part, LED pinout, absolute XDC paths, "
            "default synth flags. Use the returned absolute_path values with "
            "add_constraints. No Vivado session required."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "board": {"type": "string", "description": "Board identifier, e.g. 'red_pitaya_125_14'"}
            },
            "required": ["board"],
        },
    ),
]


def _list_boards(session, args):
    boards = list_bundled_boards()
    return {"success": True, "count": len(boards), "boards": boards}


def _get_board_info(session, args):
    board = args.get("board", "")
    info = load_board_info(board)
    if info is None:
        return err(
            f"Unknown board '{board}'. Use list_boards to see available boards.",
            available=[b["board"] for b in list_bundled_boards()],
        )
    return {"success": True, "info": info}


def _open_project(session, args):
    if (e := require_project_open(session)):
        return e
    project_path = args.get("project_path", "")
    r = session.run_tcl(f"open_project {{{project_path}}}")
    if r.success:
        session.current_project = project_path
    return {"success": r.success, "output": r.output, "elapsed_ms": r.elapsed_ms}


def _close_project(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("close_project")
    session.current_project = None
    return {"success": r.success, "output": r.output}


def _get_project_info(session, args):
    if (e := require_project_open(session)):
        return e
    commands = [
        "current_project",
        "get_property PART [current_project]",
        "get_property TARGET_LANGUAGE [current_project]",
        "get_property DIRECTORY [current_project]",
    ]
    return {cmd: session.run_tcl(cmd).output for cmd in commands}


def _create_project(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "name", "directory")):
        return e
    proj_name = args["name"]
    parent_dir = args["directory"]
    part = args.get("part", DEFAULT_PART)
    force = args.get("force", True)
    target_language = args.get("target_language", "Verilog")

    try:
        Path(parent_dir).mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        return err(f"Could not create parent directory {parent_dir}: {ex}")

    force_flag = " -force" if force else ""
    cmd = (
        f"create_project {proj_name} {{{parent_dir}/{proj_name}}} "
        f"-part {part}{force_flag}"
    )
    r = session.run_tcl(cmd, timeout_override=60)
    if not r.success:
        return {"success": False, "stage": "create_project", "error": r.output, "elapsed_ms": r.elapsed_ms}

    session.run_tcl(
        f"set_property target_language {target_language} [current_project]",
        timeout_override=30,
    )
    project_file = f"{parent_dir}/{proj_name}/{proj_name}.xpr"
    session.current_project = project_file
    return {
        "success": True,
        "project_file": project_file,
        "part": part,
        "target_language": target_language,
        "elapsed_ms": r.elapsed_ms,
    }


def _add_sources(session, args):
    if (e := require_project_open(session)):
        return e
    files = args.get("files") or []
    fileset = args.get("fileset", "sources_1")
    set_top = args.get("set_top")
    if not files:
        return err("'files' is required and must be non-empty")

    file_list = " ".join(f"{{{f}}}" for f in files)
    r = session.run_tcl(f"add_files -fileset {fileset} [list {file_list}]", timeout_override=60)
    if not r.success:
        return {"success": False, "stage": "add_files", "error": r.output}

    top_set = None
    if set_top:
        tr = session.run_tcl(
            f"set_property top {set_top} [get_filesets sources_1]; "
            f"update_compile_order -fileset sources_1",
            timeout_override=30,
        )
        if tr.success:
            top_set = set_top
        else:
            return {
                "success": False,
                "stage": "set_top",
                "error": tr.output,
                "added_count": len(files),
                "files": files,
            }
    return {
        "success": True,
        "added_count": len(files),
        "files": files,
        "top": top_set,
        "fileset": fileset,
        "elapsed_ms": r.elapsed_ms,
    }


def _add_constraints(session, args):
    if (e := require_project_open(session)):
        return e
    files = args.get("files") or []
    fileset = args.get("fileset", "constrs_1")
    if not files:
        return err("'files' is required and must be non-empty")

    file_list = " ".join(f"{{{f}}}" for f in files)
    r = session.run_tcl(f"add_files -fileset {fileset} [list {file_list}]", timeout_override=30)
    return {
        "success": r.success,
        "added_count": len(files) if r.success else 0,
        "files": files,
        "fileset": fileset,
        "output": r.output,
        "elapsed_ms": r.elapsed_ms,
    }


HANDLERS = {
    "open_project": _open_project,
    "close_project": _close_project,
    "get_project_info": _get_project_info,
    "create_project": _create_project,
    "add_sources": _add_sources,
    "add_constraints": _add_constraints,
    "list_boards": _list_boards,
    "get_board_info": _get_board_info,
}
