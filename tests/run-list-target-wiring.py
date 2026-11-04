#!/usr/bin/env python3
# Loop over all target_wiring/*.py files and list their globals.
#
# For every py-file a table of the globals with their values is printed
# to stdout, rows in alphabetical order.
#
# Additionally, all constant strings in each file (extracted via ast) are
# used as permutations of sys.platform, sys.implementation._machine and
# sys.implementation._build, including combinations of these attributes.
# Permutations whose globals differ from the baseline get an extra column
# in the table, grouped when several permutations yield identical globals.

import ast
import dataclasses
import itertools
import pathlib
import re
import types

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
TARGET_WIRING_DIR = DIRECTORY_OF_THIS_FILE / "target_wiring"

# Some wiring files query sys.platform, sys.implementation._machine and
# sys.implementation._build; the last two only exist on MicroPython. A fake
# sys is injected into their namespace; the baseline run uses values that
# are clearly marked, so conditional branches taken under the mock are
# recognizable.

# The faked sys attributes to permute: maps the field name of Permutation
# to the expression shown in column titles.
SYS_ATTRIBUTES = {
    "platform": "sys.platform",
    "machine": "sys.implementation._machine",
    "build": "sys.implementation._build",
}

# Constant strings found in the wiring files that are pin or peripheral
# names, not board identifiers: pointless to try as sys attribute values,
# so the permutations skip them. Each entry is a regular expression that
# must match the whole string.
PIN_NAMES: list[str] = [
    r"GPIO\d+",
    r"D\d+",
    r"X[1-4]",
    r"P\d+_\d+",
    r"LP[1-4]",
    r"X[A-D]",
    r"lpuart[1-4]",
    r"rx",
    r"tx",
]


def is_pin_name(string: str) -> bool:
    return any(re.fullmatch(pattern, string) for pattern in PIN_NAMES)


class FakePin:
    """Placeholder for machine.Pin, recording the constructor arguments.

    Implements __eq__ so that globals collected from different runs
    compare equal when the Pin was constructed with the same arguments.
    """

    def __init__(self, *args):
        self._args = args

    def __repr__(self) -> str:
        return "Pin(" + ", ".join(repr(arg) for arg in self._args) + ")"

    def __eq__(self, other) -> bool:
        return isinstance(other, FakePin) and self._args == other._args

    def __hash__(self) -> int:
        return hash(self._args)


@dataclasses.dataclass(frozen=True)
class Permutation:
    """The values of the faked sys attributes for one run of a wiring file."""

    platform: str = "<mock: sys.platform>"
    machine: str = "<mock: sys.implementation._machine>"
    build: str = "<mock: sys.implementation._build>"

    @property
    def overrides(self) -> dict[str, str]:
        """
        The attributes that differ from the mocked baseline.
        Example: {} for the baseline
        Example: {"machine": "ESP32-C"}
        Example: {"platform": "alif", "build": "ALIF_ENSEMBLE"}
        """
        return {
            field.name: getattr(self, field.name)
            for field in dataclasses.fields(self)
            if getattr(self, field.name) != field.default
        }

    @property
    def import_sys(self) -> types.SimpleNamespace:
        """A fake sys module exposing this permutation's attribute values."""
        return types.SimpleNamespace(
            platform=self.platform,
            implementation=types.SimpleNamespace(
                _machine=self.machine,
                _build=self.build,
            ),
        )

    @property
    def import_machine(self) -> types.SimpleNamespace:
        """A fake machine module providing a Pin placeholder."""
        return types.SimpleNamespace(Pin=FakePin)

    def collect_globals(self, code: str) -> dict[str, object]:
        """
        Execute the wiring code under this permutation and return its globals.
        Example return value: {"encoder_loopback_id": 0, "pwm_loopback_pins": [(4, 5)]}
        """
        # The wiring files only use sys.platform, sys.implementation._machine,
        # sys.implementation._build and machine.Pin. Comment out their imports
        # and inject fakes instead, so the real modules are never touched.
        code = code.replace("import sys", "# import sys")
        code = code.replace("from machine import Pin", "# from machine import Pin")
        namespace = {
            "sys": self.import_sys,
            "machine": self.import_machine,
            "Pin": self.import_machine.Pin,
        }
        injected = set(namespace)
        exec(code, namespace)
        return {
            name: value
            for name, value in namespace.items()
            if not name.startswith("__")
            and name not in injected
            and not isinstance(value, types.ModuleType)
        }


@dataclasses.dataclass(frozen=True)
class BoardVariant:
    """The globals of one wiring file for a set of sys attribute values."""

    matches: list[Permutation]
    """
    The permutations that produced these globals.
    Example: [] for the baseline
    Example: [Permutation(machine="ESP32-C"), Permutation(machine="ESP32-H2")]
    Example: [Permutation(platform="alif", build="ALIF_ENSEMBLE")]
    """

    connections: dict[str, object]
    """
    Example: {"uart_loopback_args": (1,), "uart_loopback_kwargs": {"tx": 4, "rx": 5}}
    """

    @property
    def title_lines(self) -> list[str]:
        """
        One line per match, each line the triple platform, machine, build
        with '-' for mocked attributes. Multiple lines mean 'or'.
        Example: ['-'] for the baseline
        Example: ['-, "ESP32-C", -', '-, "ESP32-H2", -']
        Example: ['"alif", -, "ALIF_ENSEMBLE"']
        """
        if not self.matches:
            return ["-"]
        return [
            ", ".join(
                f'"{match.overrides[attribute]}"'
                if attribute in match.overrides
                else "-"
                for attribute in SYS_ATTRIBUTES
            )
            for match in self.matches
        ]


class Table:
    """Renders a padded markdown table from column titles and row dicts."""

    def __init__(self, board_variants: list[BoardVariant]) -> None:
        self._board_variants = board_variants

    def render(self) -> str:
        names = sorted(
            {name for board_variant in self._board_variants for name in board_variant.connections}
        )
        """
        Example: ["pwm_loopback_pins", "uart_loopback_args"]
        """
        # The header cell of a column may span several lines ('or' of triples).
        header_cells = [["feature"]] + [
            board_variant.title_lines for board_variant in self._board_variants
        ]
        """
        Example: [["feature"], ["-"], ['-, "ESP32-C", -', '-, "ESP32-H2", -']]
        """
        data_rows = []
        for name in names:
            data_rows.append(
                [name]
                + [
                    repr(board_variant.connections[name]) if name in board_variant.connections else ""
                    for board_variant in self._board_variants
                ]
            )
            """
            Example appended row: ["spi_standalone_args_list", "[(1,), (2,)]", "[(1,)]"]
            """
        widths = [
            max(
                max(len(line) for line in header_cells[col]),
                max((len(row[col]) for row in data_rows), default=0),
            )
            for col in range(len(header_cells))
        ]
        rows = [
            [
                cell[line_index] if line_index < len(cell) else ""
                for cell in header_cells
            ]
            for line_index in range(max(len(cell) for cell in header_cells))
        ]
        rows.append(["-" * width for width in widths])
        rows.extend(data_rows)
        return "".join(
            "| "
            + " | ".join(cell.ljust(width) for cell, width in zip(row, widths))
            + " |\n"
            for row in rows
        )


class Wireing:
    """Executes a wiring file under sys attribute permutations and groups the results."""

    def __init__(self, filename: pathlib.Path) -> None:
        code = filename.read_text()
        baseline = BoardVariant([], Permutation().collect_globals(code))
        self.board_variants = [baseline]
        strings = [
            string
            for string in self._extract_constant_strings(code)
            if not is_pin_name(string)
        ]
        attributes = list(SYS_ATTRIBUTES)
        # Permute every combination of attributes, smaller combinations
        # first, so a combination is skipped when a smaller assignment
        # already explains the same globals.
        for size in range(1, len(attributes) + 1):
            for subset in itertools.combinations(attributes, size):
                for values in itertools.product(strings, repeat=size):
                    permutation = Permutation(**dict(zip(subset, values)))
                    try:
                        connections = permutation.collect_globals(code)
                    except Exception:
                        continue
                    if connections == baseline.connections:
                        continue
                    for board_variant in self.board_variants[1:]:
                        if connections == board_variant.connections:
                            dominated = any(
                                existing.overrides.items()
                                <= permutation.overrides.items()
                                for existing in board_variant.matches
                            )
                            if not dominated:
                                board_variant.matches.append(permutation)
                            break
                    else:
                        self.board_variants.append(
                            BoardVariant([permutation], connections)
                        )

    @staticmethod
    def _extract_constant_strings(code: str) -> list[str]:
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

    @property
    def table(self) -> str:
        return Table(self.board_variants).render()


def main():
    for filename in sorted(TARGET_WIRING_DIR.glob("*.py")):
        try:
            wireing = Wireing(filename)
        except Exception as e:
            print(f"{filename.name}:")
            print(f"  ERROR: {e!r}")
            print()
            continue
        print(f"{filename.name}  Table column: platform, machine, build")
        print(wireing.table)


if __name__ == "__main__":
    main()
