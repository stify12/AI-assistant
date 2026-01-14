#!/usr/bin/env python3
import json
import sys

data = json.load(sys.stdin)
items = data.get('data', {}).get('homework_items', [])
print(f"作业数量: {len(items)}")
for i, item in enumerate(items[:5]):
    print(f"{i}: page={item.get('page_num')}")
