#!/usr/bin/env python3
# Loop over all target_wiring/*.py files and list their globals.
#
# For every py-file the globals with their values are printed in
# alphabetical order to stdout.
#
# Additionally, all constant strings in each file (extracted via ast) are
# used as permutations of sys.implementation._machine. If a permutation
# yields different globals than the baseline, it is printed too.

import ast
import pathlib
import sys
import types

TARGET_WIRING_DIR = pathlib.Path(__file__).parent / "target_wiring"

# Some wiring files query sys.implementation._machine, which only exists
# on MicroPython. The baseline run mocks it with a value that is clearly
# marked, so conditional branches taken under the mock are recognizable.
MOCK_MACHINE = "<mock: sys.implementation._machine>"


def extract_constant_strings(code):
    return sorted(
        {
            node.value
            for node in ast.walk(ast.parse(code))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
    )


def collect_globals(code, machine):
    sys.implementation._machine = machine
    namespace = {}
    exec(code, namespace)
    return {
        name: value
        for name, value in namespace.items()
        if not name.startswith("__") and not isinstance(value, types.ModuleType)
    }


def print_globals(title, variables):
    print(f"{title}:")
    for name in sorted(variables):
        print(f"  {name} = {variables[name]!r}")
    print()


def main():
    for filename in sorted(TARGET_WIRING_DIR.glob("*.py")):
        code = filename.read_text()
        try:
            baseline = collect_globals(code, MOCK_MACHINE)
        except Exception as e:
            print(f"{filename.name}:")
            print(f"  ERROR: {e!r}")
            print()
            continue
        print_globals(filename.name, baseline)
        # Group machine strings that yield identical globals.
        groups = []  # list of (variables, [machines])
        for machine in extract_constant_strings(code):
            try:
                variables = collect_globals(code, machine)
            except Exception:
                continue
            if variables == baseline:
                continue
            for group_variables, machines in groups:
                if variables == group_variables:
                    machines.append(machine)
                    break
            else:
                groups.append((variables, [machine]))
        for variables, machines in groups:
            if len(machines) == 1:
                condition = f'== "{machines[0]}"'
            else:
                condition = "in (" + ", ".join(f'"{m}"' for m in machines) + ")"
            print_globals(
                f"{filename.name} sys.implementation._machine {condition}",
                variables,
            )


if __name__ == "__main__":
    main()
