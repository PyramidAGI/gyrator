import csv
from difflib import SequenceMatcher
from pathlib import Path


CSV_FILE = Path(__file__).with_name("nlcheck.csv")
TILED_WORLD_FILE = Path(__file__).with_name("tiled-world.csv")
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


def load_tiled_world_entries(path: Path) -> list[dict[str, object]]:
    dialect = detect_dialect(path)
    entries = []
    current = {"sentences": [], "rows": []}

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, dialect=dialect)
        for row in reader:
            sentence = row["natural language input"].strip()
            row_has_values = any(value.strip() for value in row.values())
            if not row_has_values:
                if current["rows"]:
                    entries.append(current)
                    current = {"sentences": [], "rows": []}
                continue

            current["rows"].append(row)
            if sentence:
                current["sentences"].append(sentence)

    if current["rows"]:
        entries.append(current)

    return entries


def parse_match(match: str) -> dict[str, str]:
    parsed = {}
    for part in match.split():
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key and value:
            parsed[key] = value
    return parsed


def append_matches_cluster(path: Path, sentence: str, matches: list[str]) -> None:
    rows_to_write = []
    for index, match in enumerate(matches):
        parsed = parse_match(match)
        row = {
            "natural language input": sentence if index == 0 else "",
            "e0": parsed.get("e0", ""),
            "e1": parsed.get("e1", ""),
            "e2": parsed.get("e2", ""),
            "e3": parsed.get("e3", ""),
            "e4": parsed.get("e4", ""),
            "v": parsed.get("v", ""),
            "threshold": parsed.get("threshold", ""),
            "message output": "",
        }
        if any(value for key, value in row.items() if key != "natural language input") or row["natural language input"]:
            rows_to_write.append(row)

    if not rows_to_write:
        return

    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["", "", "", "", "", "", "", "", ""])
        for row in rows_to_write:
            writer.writerow(
                [
                    row["natural language input"],
                    row["e0"],
                    row["e1"],
                    row["e2"],
                    row["e3"],
                    row["e4"],
                    row["v"],
                    row["threshold"],
                    row["message output"],
                ]
            )
        writer.writerow(["", "", "", "", "", "", "", "", ""])


def normalize_text(text: str) -> str:
    return " ".join(text.lower().replace("?", " ").split())


def similarity(a: str, b: str) -> float:
    normalized_a = normalize_text(a)
    normalized_b = normalize_text(b)
    score = SequenceMatcher(None, normalized_a, normalized_b).ratio()
    if normalized_a in normalized_b or normalized_b in normalized_a:
        score = max(score, 0.75)
    return score


def extract_fields(matches: list[str]) -> dict[str, set[str]]:
    fields = {"e1": set(), "e2": set(), "e3": set()}
    for match in matches:
        for part in match.split():
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            if key in fields and value:
                fields[key].add(value)
    return fields


def score_tiled_world_entry(
    sentence: str, entry: dict[str, object], expected_fields: dict[str, set[str]]
) -> tuple[int, float]:
    exact_matches = 0
    for field in ("e1", "e2", "e3"):
        cluster_values = {
            row.get(field, "").strip()
            for row in entry["rows"]
            if row.get(field, "").strip()
        }
        if cluster_values & expected_fields[field]:
            exact_matches += 1

    cluster_sentences = [str(item).strip() for item in entry["sentences"] if str(item).strip()]
    best_similarity = max((similarity(sentence, item) for item in cluster_sentences), default=0.0)
    return exact_matches, best_similarity


def build_tiled_world_result(
    entry: dict[str, object], expected_fields: dict[str, set[str]]
) -> dict[str, str]:
    cluster_sentences = [str(item).strip() for item in entry["sentences"] if str(item).strip()]
    result = {
        "natural language input": cluster_sentences[0] if cluster_sentences else "",
        "cluster size": str(len(entry["rows"])),
        "message output": "",
    }

    for row in entry["rows"]:
        message = row.get("message output", "").strip()
        if message and not result["message output"]:
            result["message output"] = message

    for field in ("e1", "e2", "e3"):
        matched_values = []
        seen = set()
        for row in entry["rows"]:
            value = row.get(field, "").strip()
            if value and value in expected_fields[field] and value not in seen:
                matched_values.append(f"{field}={value}")
                seen.add(value)
        result[field] = " ".join(matched_values)

    return result


def find_best_tiled_world_rows(
    sentence: str, entries: list[dict[str, object]], matches: list[str]
) -> list[dict[str, str]]:
    expected_fields = extract_fields(matches)
    scored_entries = []

    for index, entry in enumerate(entries):
        score = score_tiled_world_entry(sentence, entry, expected_fields)
        if score[0] > 0:
            scored_entries.append((score, index, entry))

    if not scored_entries:
        return []

    scored_entries.sort(key=lambda item: (item[0][0], item[1], item[0][1]), reverse=True)
    best_entry = scored_entries[0][2]
    return [build_tiled_world_result(best_entry, expected_fields)]


def format_tiled_world_row(row: dict[str, str]) -> str:
    parts = []
    for field in ("e1", "e2", "e3"):
        value = row.get(field, "").strip()
        if value:
            parts.append(value)

    message = row.get("message output", "").strip()
    sentence = row.get("natural language input", "").strip()
    cluster_size = row.get("cluster size", "0").strip()
    return f"NL={sentence} cluster_size={cluster_size} message={message} {' '.join(parts)}"


def print_result(source: str, value: str) -> None:
    print(f"{source}: {value}")


def find_matches(sentence: str, rules: list[tuple[str, str]]) -> list[str]:
    matches = []
    normalized = sentence

    if "?" in normalized:
        matches.append(QUESTION_OUTPUT)
        normalized = normalized.replace("?", " ")

    lowered = normalized.lower()
    matches.extend(output for pattern, output in rules if pattern in lowered)
    return matches


def is_question_match(match: str) -> bool:
    return any(part == "e0=question" for part in match.split())


def main() -> None:
    rules = load_rules(CSV_FILE)
    tiled_world_entries = load_tiled_world_entries(TILED_WORLD_FILE)
    print(f"Loaded {len(rules)} rules from {CSV_FILE.name}")

    while True:
        sentence = input("Enter a sentence: ").strip()
        if sentence.lower() == "quit":
            break

        matches = find_matches(sentence, rules)
        if matches:
            has_question = any(is_question_match(match) for match in matches)
            for match in matches:
                source = "built-in" if match == QUESTION_OUTPUT and "?" in sentence else CSV_FILE.name
                print_result(source, match)
            if has_question:
                best_rows = find_best_tiled_world_rows(sentence, tiled_world_entries, matches)
                for row in best_rows:
                    print_result(TILED_WORLD_FILE.name, format_tiled_world_row(row))
            else:
                append_matches_cluster(TILED_WORLD_FILE, sentence, matches)
                tiled_world_entries = load_tiled_world_entries(TILED_WORLD_FILE)
        else:
            print("No matches.")


if __name__ == "__main__":
    main()
