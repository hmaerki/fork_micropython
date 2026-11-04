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
    def title(self) -> str:
        """
        Example: '-' for the baseline
        Example: 'sys.implementation._machine in ("ESP32-C", "ESP32-H2")'
        Example: 'sys.platform == "alif" and sys.implementation._build == "ALIF_ENSEMBLE"'
        """
        if not self.matches:
            return "-"
        parts = []
        # Combine single-attribute matches per attribute: == or in (...).
        for attribute, expression in SYS_ATTRIBUTES.items():
            values = [
                match.overrides[attribute]
                for match in self.matches
                if list(match.overrides) == [attribute]
            ]
            if not values:
                continue
            if len(values) == 1:
                parts.append(f'{expression} == "{values[0]}"')
            else:
                quoted = ", ".join(f'"{v}"' for v in values)
                parts.append(f"{expression} in ({quoted})")
        # Multi-attribute matches become 'a == x and b == y' conjunctions.
        conjunctions = [
            " and ".join(
                f'{SYS_ATTRIBUTES[attribute]} == "{value}"'
                for attribute, value in match.overrides.items()
            )
            for match in self.matches
            if len(match.overrides) > 1
        ]
        if len(parts) + len(conjunctions) > 1:
            conjunctions = [f"({c})" for c in conjunctions]
        return " or ".join(parts + conjunctions)


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
    """Executes a wiring file under sys attribute permutations and groups the results."""

    def __init__(self, filename: pathlib.Path) -> None:
        code = filename.read_text()
        baseline = BoardVariant([], self._collect_globals(code))
        self.board_variants = [baseline]
        strings = self._extract_constant_strings(code)
        attributes = list(SYS_ATTRIBUTES)
        # Permute every combination of attributes, smaller combinations
        # first, so a combination is skipped when a smaller assignment
        # already explains the same globals.
        for size in range(1, len(attributes) + 1):
            for subset in itertools.combinations(attributes, size):
                for values in itertools.product(strings, repeat=size):
                    permutation = Permutation(**dict(zip(subset, values)))
                    try:
                        connections = self._collect_globals(code, permutation)
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

    @staticmethod
    def _collect_globals(
        code: str, permutation: Permutation = Permutation()
    ) -> dict[str, object]:
        """
        Example return value: {"encoder_loopback_id": 0, "pwm_loopback_pins": [(4, 5)]}
        """
        # The wiring files only use sys.platform, sys.implementation._machine
        # and sys.implementation._build. Comment out their 'import sys' and
        # inject a fake instead, so the real sys module is never touched.
        fake_sys = types.SimpleNamespace(
            platform=permutation.platform,
            implementation=types.SimpleNamespace(
                _machine=permutation.machine,
                _build=permutation.build,
            ),
        )
        code = code.replace("import sys", "# import sys")
        namespace = {"sys": fake_sys}
        exec(code, namespace)
        return {
            name: value
            for name, value in namespace.items()
            if not name.startswith("__")
            and name != "sys"
            and not isinstance(value, types.ModuleType)
        }

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
        print(filename.name)
        print(wireing.table)


if __name__ == "__main__":
    main()
