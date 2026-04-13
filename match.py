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

def entry_score(query, entry):
    """Best similarity across the NL sentence and all tile values."""
    candidates = [entry['sentence']]
    tile_cols = ['e0', 'e1', 'e2', 'e3', 'e4', 'v', 'threshold', 'message output']
    for row in entry['rows']:
        for col in tile_cols:
            val = row.get(col, '').strip()
            if val:
                candidates.append(val)
    return max(similarity(query, c) for c in candidates)

def find_best_match(entries, query):
    scored = [(entry_score(query, e), e) for e in entries]
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

def add_entry(path, query):
    parts = query.split(' ')
    e0 = parts[0] if len(parts) > 0 else ''
    e1 = parts[1] if len(parts) > 1 else ''
    e2 = parts[2] if len(parts) > 2 else ''
    e3 = parts[3] if len(parts) > 3 else ''
    with open(path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['placeholder', e0, e1, e2, e3, '', '', '', 'empty message'])
    print(f"  Added: nl=placeholder  e0={e0}  e1={e1}  e2={e2}  e3={e3}  message output=empty message")

def main():
    entries = load_entries(CSV_FILE)
    print(f"Loaded {len(entries)} entries from {CSV_FILE}")
    print("Type 'quit' to exit. Start with 'a ' to add a new tile row.\n")
    while True:
        query = input("Enter a sentence: ").strip()
        if not query or query.lower() == 'quit':
            break
        if query.startswith('a '):
            add_entry(CSV_FILE, query)
        else:
            score, entry = find_best_match(entries, query)
            if entry:
                print_entry(score, entry)
            else:
                print("No entries found.")
        print()

if __name__ == "__main__":
    main()
