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
import dataclasses
import pathlib
import sys
import types

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
TARGET_WIRING_DIR = DIRECTORY_OF_THIS_FILE / "target_wiring"

# Some wiring files query sys.implementation._machine, which only exists
# on MicroPython. The baseline run mocks it with a value that is clearly
# marked, so conditional branches taken under the mock are recognizable.
MOCK_MACHINE = "<mock: sys.implementation._machine>"


@dataclasses.dataclass
class BoardVariant:
    """The globals of one wiring file for a set of machine strings."""

    machines: list
    """
    Example: [] for the baseline
    Example: ["ESP32-C", "ESP32-H2"]
    """

    connections: dict
    """
    Example: {"uart_loopback_args": (1,), "uart_loopback_kwargs": {"tx": 4, "rx": 5}}
    """

    @property
    def title(self):
        """
        Example: '-' for the baseline
        Example: 'sys.implementation._machine == "Teensy"'
        Example: 'sys.implementation._machine in ("ESP32-C", "ESP32-H2")'
        """
        if not self.machines:
            return "-"
        if len(self.machines) == 1:
            return f'sys.implementation._machine == "{self.machines[0]}"'
        quoted = ", ".join(f'"{m}"' for m in self.machines)
        return f"sys.implementation._machine in ({quoted})"


class Table:
    """Renders a padded markdown table from column titles and row dicts."""

    def __init__(self, board_variants):
        self._board_variants = board_variants

    def __str__(self):
        names = sorted(
            {name for board_variant in self._board_variants for name in board_variant.connections}
        )
        """
        Example: ["pwm_loopback_pins", "uart_loopback_args"]
        """
        header = ["feature"] + [board_variant.title for board_variant in self._board_variants]
        """
        Example: ["feature", "-", 'sys.implementation._machine in ("ESP32-C", "ESP32-H2")']
        """
        rows = [header]
        for name in names:
            rows.append(
                [name]
                + [
                    repr(board_variant.connections[name]) if name in board_variant.connections else ""
                    for board_variant in self._board_variants
                ]
            )
            """
            Example appended row: ["spi_standalone_args_list", "[(1,), (2,)]", "[(1,)]"]
            """
        widths = [max(len(row[col]) for row in rows) for col in range(len(header))]
        rows.insert(1, ["-" * width for width in widths])
        return "".join(
            "| "
            + " | ".join(cell.ljust(width) for cell, width in zip(row, widths))
            + " |\n"
            for row in rows
        )


class Wireing:
    """Executes a wiring file under machine permutations and groups the results."""

    def __init__(self, filename):
        code = filename.read_text()
        baseline = BoardVariant([], self._collect_globals(code, MOCK_MACHINE))
        self.board_variants = [baseline]
        for machine in self._extract_constant_strings(code):
            try:
                connections = self._collect_globals(code, machine)
            except Exception:
                continue
            if connections == baseline.connections:
                continue
            for board_variant in self.board_variants[1:]:
                if connections == board_variant.connections:
                    board_variant.machines.append(machine)
                    break
            else:
                self.board_variants.append(BoardVariant([machine], connections))

    @staticmethod
    def _extract_constant_strings(code):
        """
        Example return value: ["ESP32-C", "ESP32-H2", "rx", "tx"]
        """
        return sorted(
            {
                node.value
                for node in ast.walk(ast.parse(code))
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            }
        )

    @staticmethod
    def _collect_globals(code, machine):
        """
        Example return value: {"encoder_loopback_id": 0, "pwm_loopback_pins": [(4, 5)]}
        """
        sys.implementation._machine = machine
        namespace = {}
        exec(code, namespace)
        return {
            name: value
            for name, value in namespace.items()
            if not name.startswith("__") and not isinstance(value, types.ModuleType)
        }

    @property
    def table(self):
        return str(Table(self.board_variants))


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
