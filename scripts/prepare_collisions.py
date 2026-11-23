"""Attach the reviewed A4 primary-factor classification to the BPD snapshot."""
import csv
from collections import Counter
from pathlib import Path


def classify_collisions(rows, mapping):
    """Return a list of CSV row dictionaries with alcohol_pcf_status added.

    rows is an iterable of CSV row dictionaries; mapping maps exact PCF
    descriptions to reviewed statuses. Reject unreviewed labels and missing
    or repeated ObjectId values so counts remain reproducible.
    """
    events = []
    seen = set()
    for row in rows:
        # A repeated event ID would inflate all downstream collision counts.
        key = row['ObjectId'].strip()
        if not key or key in seen:
            raise ValueError(f'Missing or repeated ObjectId: {key!r}')
        seen.add(key)
        # Require explicit review of new labels before publishing A4 counts.
        label = row['PCF Description']
        if label not in mapping:
            raise ValueError(f'Review new PCF description: {label!r}')
        events.append(dict(row, alcohol_pcf_status=mapping[label]))
    return events


def main():
    """Take no arguments, write the classified collision CSV, and return None."""
    with Path('data/mappings/collision_pcf.csv').open(newline='', encoding='utf-8') as source:
        mapping = {r['description']: r['status'] for r in csv.DictReader(source)}
    with Path('data/raw/collision_data.csv').open(newline='', encoding='utf-8-sig') as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames + ['alcohol_pcf_status']
        events = classify_collisions(reader, mapping)
    # Write only after all input rows have passed validation.
    out = Path('data/processed/collisions.csv')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', newline='', encoding='utf-8') as dest:
        writer = csv.DictWriter(dest, fieldnames=fields)
        writer.writeheader()
        writer.writerows(events)
    print(len(events), dict(Counter(r['alcohol_pcf_status'] for r in events)))


if __name__ == '__main__':
    main()
