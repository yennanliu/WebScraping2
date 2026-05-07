import csv
import os
import re

def clean_text(text):
    if not text:
        return ''
    # Strip whitespace
    text = text.strip()
    # Remove suffixes like "Sent from JPTT..."
    text = re.sub(r'Sent from JPTT.*', '', text)
    # Remove long dashes
    text = re.sub(r'—+', '', text)
    # Remove ==
    text = re.sub(r'==+', '', text)
    # Remove ! and :
    text = re.sub(r'[!:]+', '', text)
    # Remove multiple quotes
    text = re.sub(r'"+', '', text)
    # Replace multiple spaces/newlines with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def main():
    input_file = 'data/raw/蝦皮_20260506_155631.csv'
    output_file = 'data/processed/processed_蝦皮_20260506_155631.csv'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    seen_urls = set()
    
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
        writer.writeheader()
        
        for row in reader:
            url = row['url'].strip()
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            row['title'] = clean_text(row['title'])
            row['author'] = clean_text(row['author'])
            row['content'] = clean_text(row['content'])
            
            # Skip if content empty
            if not row['content']:
                continue
            
            writer.writerow(row)

if __name__ == '__main__':
    main()