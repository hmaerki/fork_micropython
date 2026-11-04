#!/usr/bin/env python3
# Loop over all target_wiring/*.py files and list their globals.
#
# For every py-file a table of the globals with their values is printed
# to stdout, rows in alphabetical order.
#
# Additionally, all constant strings in each file (extracted via ast) are
# used as permutations of sys.implementation._machine. Permutations whose
# globals differ from the baseline get an extra column in the table,
# grouped when several machine strings yield identical globals.

import ast
import pathlib
import sys
import types

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
TARGET_WIRING_DIR = DIRECTORY_OF_THIS_FILE / "target_wiring"

# Some wiring files query sys.implementation._machine, which only exists
# on MicroPython. The baseline run mocks it with a value that is clearly
# marked, so conditional branches taken under the mock are recognizable.
MOCK_MACHINE = "<mock: sys.implementation._machine>"


class Wireing:
    def __init__(self, filename):
        code = filename.read_text()
        baseline = self._collect_globals(code, MOCK_MACHINE)
        # variants: list of (title, variables), baseline first.
        self._variants = [("-", baseline)]
        for variables, machines in self._collect_groups(code, baseline):
            if len(machines) == 1:
                condition = f'== "{machines[0]}"'
            else:
                condition = "in (" + ", ".join(f'"{m}"' for m in machines) + ")"
            self._variants.append(
                (f"sys.implementation._machine {condition}", variables)
            )

    @staticmethod
    def _extract_constant_strings(code):
        return sorted(
            {
                node.value
                for node in ast.walk(ast.parse(code))
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            }
        )

    @staticmethod
    def _collect_globals(code, machine):
        sys.implementation._machine = machine
        namespace = {}
        exec(code, namespace)
        return {
            name: value
            for name, value in namespace.items()
            if not name.startswith("__") and not isinstance(value, types.ModuleType)
        }

    def _collect_groups(self, code, baseline):
        # Group machine strings that yield identical globals.
        groups = []  # list of (variables, [machines])
        for machine in self._extract_constant_strings(code):
            try:
                variables = self._collect_globals(code, machine)
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
        return groups

    @property
    def table(self):
        names = sorted(
            {name for _, variables in self._variants for name in variables}
        )
        header = ["feature"] + [title for title, _ in self._variants]
        rows = [header]
        for name in names:
            rows.append(
                [name]
                + [
                    repr(variables[name]) if name in variables else ""
                    for _, variables in self._variants
                ]
            )
        widths = [max(len(row[col]) for row in rows) for col in range(len(header))]
        rows.insert(1, ["-" * width for width in widths])
        return "".join(
            "| "
            + " | ".join(cell.ljust(width) for cell, width in zip(row, widths))
            + " |\n"
            for row in rows
        )


def main():
    for filename in sorted(TARGET_WIRING_DIR.glob("*.py")):
        try:
            wireing = Wireing(filename)
        except Exception as e:
            print(f"{filename.name}:")
            print(f"  ERROR: {e!r}")
            print()
            continue
        print(filename.name)
        print(wireing.table)


if __name__ == "__main__":
    main()
