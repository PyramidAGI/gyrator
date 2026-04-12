import csv
from difflib import SequenceMatcher

CSV_FILE = "tiled-world.csv"

def load_entries(path):
    """Load CSV into a list of (sentence, [rows]) entries, grouping continuation rows."""
    entries = []
    current = None
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            sentence = row['natural language input'].strip()
            if sentence:
                current = {'sentence': sentence, 'rows': [row]}
                entries.append(current)
            elif current is not None:
                # continuation row (no NL input) belongs to previous entry
                current['rows'].append(row)
    return entries

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_best_match(entries, query):
    scored = [(similarity(query, e['sentence']), e) for e in entries]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0] if scored else (0, None)

def print_entry(score, entry):
    print(f"\nBest match ({score:.0%}): \"{entry['sentence']}\"")
    print("-" * 50)
    headers = ['e0', 'e1', 'e2', 'e3', 'e4', 'v', 'threshold', 'message output']
    for row in entry['rows']:
        values = {h: row.get(h, '').strip() for h in headers}
        non_empty = {k: v for k, v in values.items() if v}
        if non_empty:
            print("  " + "  |  ".join(f"{k}: {v}" for k, v in non_empty.items()))

def main():
    entries = load_entries(CSV_FILE)
    print(f"Loaded {len(entries)} entries from {CSV_FILE}")
    print("Type 'quit' to exit.\n")
    while True:
        query = input("Enter a sentence: ").strip()
        if not query or query.lower() == 'quit':
            break
        score, entry = find_best_match(entries, query)
        if entry:
            print_entry(score, entry)
        else:
            print("No entries found.")
        print()

if __name__ == "__main__":
    main()
