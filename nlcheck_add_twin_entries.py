import argparse
import csv
import re
from pathlib import Path


CSV_FILE = Path(__file__).with_name("nlcheck.csv")
ENTITY_SUFFIX_PATTERN = re.compile(r"\d+$")


def normalize_twin_output(output: str) -> str:
    normalized_parts = []
    for part in output.split():
        if "=" not in part:
            normalized_parts.append(part)
            continue

        key, value = part.split("=", 1)
        if key.startswith("e") and ENTITY_SUFFIX_PATTERN.search(value):
            value = ENTITY_SUFFIX_PATTERN.sub("000", value)
        normalized_parts.append(f"{key}={value}")

    return " ".join(normalized_parts)


def build_twin_entry(pattern: str, output: str) -> tuple[str, str] | None:
    if not pattern.lower().startswith("the "):
        return None

    twin_pattern = f"a {pattern[4:]}"
    twin_output = normalize_twin_output(output)
    return twin_pattern, twin_output


def ensure_trailing_newline(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return

    with path.open("rb") as handle:
        handle.seek(-1, 2)
        last_byte = handle.read(1)

    if last_byte not in {b"\n", b"\r"}:
        with path.open("a", encoding="utf-8-sig", newline="") as handle:
            handle.write("\n")


def append_twin_entries(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        rows = list(reader)

    if not rows:
        return 0

    existing_entries = {
        (row[0].strip(), row[1].strip())
        for row in rows[1:]
        if len(row) >= 2 and row[0].strip()
    }

    entries_to_append = []
    for row in rows[1:]:
        if len(row) < 2:
            continue

        pattern = row[0].strip()
        output = row[1].strip()
        twin_entry = build_twin_entry(pattern, output)
        if twin_entry is None or twin_entry in existing_entries:
            continue

        entries_to_append.append(twin_entry)
        existing_entries.add(twin_entry)

    if not entries_to_append:
        return 0

    ensure_trailing_newline(path)
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        for pattern, output in entries_to_append:
            writer.writerow([pattern, output])

    return len(entries_to_append)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append missing 'a ...' twin entries for rows that start with 'the '."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=CSV_FILE,
        type=Path,
        help="CSV file to update (defaults to nlcheck.csv next to this script)",
    )
    args = parser.parse_args()

    added_count = append_twin_entries(args.csv_path)
    print(f"Added {added_count} twin entries to {args.csv_path.name}")


if __name__ == "__main__":
    main()
