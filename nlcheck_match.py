import csv
from pathlib import Path


CSV_FILE = Path(__file__).with_name("nlcheck.csv")
QUESTION_OUTPUT = "e0=question"


def detect_dialect(path: Path) -> csv.Dialect:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(2048)
    return csv.Sniffer().sniff(sample, delimiters=",;")


def load_rules(path: Path) -> list[tuple[str, str]]:
    dialect = detect_dialect(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, dialect)
        rows = [row for row in reader if any(cell.strip() for cell in row)]

    if not rows:
        return []

    header = rows[0]
    output_index = None
    for index, name in enumerate(header):
        if name.strip().lower() == "output":
            output_index = index
            break

    if output_index is None:
        output_index = 1 if len(header) > 1 else 0

    rules = []
    for row in rows[1:]:
        if not row:
            continue

        pattern = row[0].strip()
        if not pattern:
            continue

        output = row[output_index].strip() if output_index < len(row) else ""
        if pattern == "?":
            continue

        rules.append((pattern.lower(), output))

    return rules


def find_matches(sentence: str, rules: list[tuple[str, str]]) -> list[str]:
    matches = []
    normalized = sentence

    if "?" in normalized:
        matches.append(QUESTION_OUTPUT)
        normalized = normalized.replace("?", " ")

    lowered = normalized.lower()
    matches.extend(output for pattern, output in rules if pattern in lowered)
    return matches


def main() -> None:
    rules = load_rules(CSV_FILE)
    print(f"Loaded {len(rules)} rules from {CSV_FILE.name}")

    while True:
        sentence = input("Enter a sentence: ").strip()
        if sentence.lower() == "quit":
            break

        matches = find_matches(sentence, rules)
        if matches:
            for match in matches:
                print(match)
        else:
            print("No matches.")


if __name__ == "__main__":
    main()
