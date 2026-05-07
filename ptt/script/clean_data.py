import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from clean import clean_content


def clean_row(row: dict) -> dict | None:
    row["title"]   = row["title"].strip()
    row["author"]  = row["author"].strip()
    row["content"] = clean_content(row["content"])
    if not row["content"]:
        return None
    return row


def main():
    input_file  = "data/raw/蝦皮_20260506_155631.csv"
    output_file = "data/processed/processed_蝦皮_20260506_155631.csv"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    seen_urls = set()

    with open(input_file, "r", encoding="utf-8") as infile, \
         open(output_file, "w", encoding="utf-8", newline="") as outfile:

        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
        writer.writeheader()

        for row in reader:
            url = row["url"].strip()
            if url in seen_urls:
                continue
            seen_urls.add(url)

            cleaned = clean_row(row)
            if cleaned:
                writer.writerow(cleaned)


if __name__ == "__main__":
    main()
