from collections.abc import Mapping
import readline
import shlex
import subprocess
import sys
import pathlib
import os
from typing import Final, TextIO

SHELL_BUILTINS: Final[list[str]] = [
    "echo",
    "exit",
    "type",
    "pwd",
    "cd",
]

PROGRAMS_IN_PATH: dict[str, pathlib.Path] = {}

def parse_programs_in_path(path: str, programs: dict[str, pathlib.Path]) -> None:
    for dir in path.split(os.pathsep):
        try:
            for entry in pathlib.Path(dir).iterdir():
                if entry.is_file() and os.access(entry, os.X_OK):
                    programs[entry.name] = entry
        except FileNotFoundError:
            continue

parse_programs_in_path(os.getenv("PATH", ""), PROGRAMS_IN_PATH)

COMPLETIONS: Final[list[str]] = sorted([*SHELL_BUILTINS, *PROGRAMS_IN_PATH.keys()])

def display_matches(substitution, matches, longest_match_length):
    print()
    if matches:
        print("  ".join(sorted(matches)))
    print("$ " + substitution, end="")

def complete(text: str, state: int) -> str | None:
    matches = sorted(set([s for s in COMPLETIONS if s.startswith(text)]))
    if len(matches) == 1:
        return matches[state] + " " if state < len(matches) else None
    return matches[state] if state < len(matches) else None

readline.set_completion_display_matches_hook(display_matches)
readline.parse_and_bind("tab: complete")
readline.set_completer(complete)

def main():
    while True:
        sys.stdout.write("$ ")
        cmds = shlex.split(input())
        out, err = sys.stdout, sys.stderr
        close_out, close_err = False, False
        try:
            if ">" in cmds:
                out_index = cmds.index(">")
                out = open(cmds[out_index + 1], "w")
                close_out = True
                cmds = cmds[:out_index] + cmds[out_index + 2 :]
            elif "1>" in cmds:
                out_index = cmds.index("1>")
                out = open(cmds[out_index + 1], "w")
                close_out = True
                cmds = cmds[:out_index] + cmds[out_index + 2 :]
            if "2>" in cmds:
                out_index = cmds.index("2>")
                err = open(cmds[out_index + 1], "w")
                close_err = True
                cmds = cmds[:out_index] + cmds[out_index + 2 :]
            if ">>" in cmds:
                out_index = cmds.index(">>")
                out = open(cmds[out_index + 1], "a")
                close_out = True
                cmds = cmds[:out_index] + cmds[out_index + 2 :]
            elif "1>>" in cmds:
                out_index = cmds.index("1>>")
                out = open(cmds[out_index + 1], "a")
                close_out = True
                cmds = cmds[:out_index] + cmds[out_index + 2 :]
            if "2>>" in cmds:
                out_index = cmds.index("2>>")
                err = open(cmds[out_index + 1], "a")
                close_err = True
                cmds = cmds[:out_index] + cmds[out_index + 2 :]
            handle_all(cmds, out, err)
        finally:
            if close_out:
                out.close()
            if close_err:
                err.close()

def handle_all(cmds: list[str], out: TextIO, err: TextIO):
    match cmds:
        case ["echo", *s]:
            out.write(" ".join(s) + "\n")
        case ["type", s]:
            type_command(s, out, err)
        case ["exit", "0"]:
            sys.exit(0)
        case ["pwd"]:
            out.write(f"{os.getcwd()}\n")
        case ["cd", dir]:
            cd(dir, out, err)
        case [cmd, *args] if cmd in PROGRAMS_IN_PATH:
            process = subprocess.Popen([cmd, *args], stdout=out, stderr=err)
            process.wait()
        case command:
            out.write(f"{' '.join(command)}: command not found\n")

def type_command(command: str, out: TextIO, err: TextIO):
    if command in SHELL_BUILTINS:
        out.write(f"{command} is a shell builtin\n")
        return
    if command in PROGRAMS_IN_PATH:
        out.write(f"{command} is {PROGRAMS_IN_PATH[command]}\n")
        return
    out.write(f"{command}: not found\n")

def cd(path: str, out: TextIO, err: TextIO) -> None:
    if path.startswith("~"):
        home = os.getenv("HOME") or "/root"
        path = path.replace("~", home)
    p = pathlib.Path(path)
    if not p.exists():
        out.write(f"cd: {path}: No such file or directory\n")
        return
    os.chdir(p)

if __name__ == "__main__":
    main()
