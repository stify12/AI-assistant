#!/usr/bin/env python3
import json

with open('datasets/fa2e6320.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Dataset ID: {data['dataset_id']}")
print(f"Book ID: {data['book_id']}")
print(f"Pages: {data['pages']}")
print(f"Base effects keys: {list(data['base_effects'].keys())}")
print()

for page, questions in data['base_effects'].items():
    print(f"Page {page}: {len(questions)} questions")
