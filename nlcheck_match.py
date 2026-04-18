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
            if sentence:
                current["sentences"].append(sentence)
                current["rows"].append(row)
                continue

            if current["rows"]:
                entries.append(current)
                current = {"sentences": [], "rows": []}

    if current["rows"]:
        entries.append(current)

    return entries


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


def score_tiled_world_row(
    sentence: str, row: dict[str, str], expected_fields: dict[str, set[str]]
) -> tuple[int, float]:
    exact_matches = 0
    for field in ("e1", "e2", "e3"):
        value = row.get(field, "").strip()
        if value and value in expected_fields[field]:
            exact_matches += 1

    return exact_matches, similarity(sentence, row.get("natural language input", ""))


def find_best_tiled_world_rows(
    sentence: str, entries: list[dict[str, object]], matches: list[str]
) -> list[dict[str, str]]:
    expected_fields = extract_fields(matches)
    scored_rows = []

    for entry in entries:
        cluster_sentences = [str(item).strip() for item in entry["sentences"] if str(item).strip()]
        primary_sentence = cluster_sentences[0] if cluster_sentences else ""
        for raw_row in entry["rows"]:
            row = dict(raw_row)
            row["natural language input"] = primary_sentence
            row["cluster sentence count"] = str(len(cluster_sentences))
            scored_rows.append((score_tiled_world_row(sentence, row, expected_fields), row))

    if not scored_rows:
        return []

    scored_rows.sort(key=lambda item: item[0], reverse=True)
    best_score = scored_rows[0][0]
    return [row for score, row in scored_rows if score == best_score and score[0] > 0]


def format_tiled_world_row(row: dict[str, str]) -> str:
    parts = []
    for field in ("e1", "e2", "e3"):
        value = row.get(field, "").strip()
        if value:
            parts.append(f"{field}={value}")

    message = row.get("message output", "").strip()
    sentence = row.get("natural language input", "").strip()
    cluster_sentence_count = row.get("cluster sentence count", "0").strip()
    return f"NL={sentence} cluster_size={cluster_sentence_count} message={message} {' '.join(parts)}"


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
            for match in matches:
                source = "built-in" if match == QUESTION_OUTPUT and "?" in sentence else CSV_FILE.name
                print_result(source, match)
            if QUESTION_OUTPUT in matches:
                best_rows = find_best_tiled_world_rows(sentence, tiled_world_entries, matches)
                for row in best_rows:
                    print_result(TILED_WORLD_FILE.name, format_tiled_world_row(row))
        else:
            print("No matches.")


if __name__ == "__main__":
    main()
