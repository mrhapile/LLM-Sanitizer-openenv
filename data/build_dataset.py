import json
import random

OUTPUT_FILE = "data/dataset.jsonl"
GOLD_FILE = "data/gold_manifest.json"

samples = []
gold = []

EMAIL_TEMPLATES = [
    "Re: Meeting update\nHi team,\nPlease contact me at {email}\nAlso API_KEY={api_key}\nThanks,\n{name}",
    "Forwarded message:\n{name} ({role}) shared credentials:\nAPI_KEY={api_key}\nEmail: {email}",
    "Hey,\nCall me at {phone}\nEmail: {email}\nAlso check this key: {api_key}\n-{name}",
    "Re: Urgent\n{name}, the {role}, needs access.\nEmail: {email}\nAPI_KEY={api_key}"
]

NAMES = ["Akash", "John", "Sarah"]
ROLES = ["CFO", "CTO", "Manager"]
EMAILS = ["akash@gmail.com", "john@yahoo.com"]
PHONES = ["9876543210", "9123456780"]
API_KEYS = ["sk-1234567890abcd", "sk-abcdef1234567890"]
NOISE = ["\n\nSent from iPhone", "\n---\nConfidential", "\n\nThanks!"]

for i in range(15):  # small dataset (IMPORTANT)
    template = random.choice(EMAIL_TEMPLATES)

    name = random.choice(NAMES)
    role = random.choice(ROLES)
    email = random.choice(EMAILS)
    phone = random.choice(PHONES)
    api_key = random.choice(API_KEYS)

    text = template.format(
        name=name,
        role=role,
        email=email,
        phone=phone,
        api_key=api_key
    )

    text += random.choice(NOISE)

    samples.append({"id": i, "input": text})

    gold.append({
        "id": i,
        "email": email,
        "phone": phone,
        "api_key": api_key,
        "name": name,
        "role": role
    })

with open(OUTPUT_FILE, "w") as f:
    for s in samples:
        f.write(json.dumps(s) + "\n")

with open(GOLD_FILE, "w") as f:
    json.dump(gold, f, indent=2)

print(f"Generated {len(samples)} samples to {OUTPUT_FILE} and {GOLD_FILE}.")
