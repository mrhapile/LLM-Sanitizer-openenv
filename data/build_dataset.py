import json
import random

random.seed(42)  # Deterministic generation for reproducibility

OUTPUT_FILE = "data/dataset.jsonl"
GOLD_FILE = "data/gold_manifest.json"

samples = []
gold = []

# --- Expanded template pool for real-world variability ---

EMAIL_TEMPLATES = [
    # Original templates
    "Re: Meeting update\nHi team,\nPlease contact me at {email}\nAlso API_KEY={api_key}\nThanks,\n{name}",
    "Forwarded message:\n{name} ({role}) shared credentials:\nAPI_KEY={api_key}\nEmail: {email}",
    "Hey,\nCall me at {phone}\nEmail: {email}\nAlso check this key: {api_key}\n-{name}",
    "Re: Urgent\n{name}, the {role}, needs access.\nEmail: {email}\nAPI_KEY={api_key}",

    # New templates - corporate memos
    "MEMO: Internal\nFrom: {name}\nSubject: System Access\n\nPlease update the API credentials:\nNew key: {api_key}\nContact {email} for verification.\nPhone: {phone}",
    "To: Engineering Team\nFrom: {name}, {role}\n\nAttaching new service credentials below.\nAPI_KEY={api_key}\nFor questions reach out to {email}",
    "Hi all,\n{name} (our {role}) has requested a key rotation.\nOld key revoked. New key: {api_key}\nReach {name} at {email} or {phone}.",

    # New templates - Slack-style messages
    "#{name} posted in #credentials:\n> New staging key: {api_key}\n> Contact: {email}\n> Phone for emergencies: {phone}",
    "@{name} shared a file in #ops-secrets:\napi_key = {api_key}\nbackup email: {email}\nCall {phone} if issues",
    "Thread: Security Update\n{name} ({role}): I've rotated the key.\nHere's the new one: {api_key}\nEmail me at {email} to confirm.",

    # New templates - support tickets
    "Ticket #4821\nReporter: {name} ({role})\nDescription: Cannot authenticate with key {api_key}\nContact: {email}\nCallback: {phone}",
    "JIRA-2847 assigned to {name}\nNotes: Investigate leaked credential {api_key}\nReporter email: {email}\nEscalation contact: {phone}",

    # New templates - onboarding docs
    "Welcome aboard!\nName: {name}\nRole: {role}\nEmail: {email}\nPhone: {phone}\nProvisioned API Key: {api_key}\n\nPlease change your credentials within 24 hours.",
    "New hire checklist for {name}:\n1. Verify email: {email}\n2. Set up 2FA on phone: {phone}\n3. Test API access with key: {api_key}\n4. Report to {role} orientation",

    # New templates - incident reports
    "INCIDENT REPORT\nSeverity: High\nReported by: {name}, {role}\nExposed credential: {api_key}\nNotify: {email}\nHotline: {phone}\n\nImmediate rotation required.",
    "Postmortem: API Key Leak\nThe key {api_key} was found in a public repo.\n{name} ({role}) has been notified at {email}.\nFor urgent matters call {phone}.",

    # New templates - email chains
    "On Mon, {name} wrote:\n> Can you send me the API key?\n> My email is {email}\n\nSure, here it is: {api_key}\nCall me at {phone} if it doesn't work.\n\n-- {name}, {role}",
    "---------- Forwarded ----------\nFrom: {name} <{email}>\nRole: {role}\n\nPlease use this key for the staging environment:\n{api_key}\n\nMy direct line is {phone}.",

    # New templates - config file leaks
    "# config.yaml dump\nowner: {name}\nrole: {role}\napi_key: {api_key}\ncontact_email: {email}\nphone: {phone}\n# DO NOT COMMIT",
    "ENV_DUMP:\nUSER={name}\nROLE={role}\nAPI_SECRET={api_key}\nEMAIL={email}\nPHONE={phone}",

    # New templates - meeting notes
    "Meeting Notes - Q3 Review\nAttendees: {name} ({role})\nAction items:\n- Rotate API key {api_key}\n- Update contact to {email}\n- Emergency line: {phone}",
    "Standup Notes:\n{name} mentioned the {role} dashboard is down.\nDebug key: {api_key}\nReach {name} at {email} or {phone} for status.",

    # New templates - documentation
    "## API Access Guide\nMaintainer: {name} ({role})\nProduction Key: {api_key}\nSupport: {email}\nOn-call: {phone}\n\nRotate keys monthly.",
    "README - Internal Services\nPoint of contact: {name}, our {role}\nService key: {api_key}\nEmail for access requests: {email}\nDirect: {phone}",
]

NAMES = [
    "Akash", "John", "Sarah", "Maria", "David", "Lisa",
    "James", "Elena", "Raj", "Priya", "Michael", "Angela",
    "Carlos", "Fatima", "Wei", "Natasha", "Omar", "Sophie",
    "Dmitri", "Yuki"
]

ROLES = [
    "CFO", "CTO", "CEO", "Manager", "Director",
    "VP of Engineering", "Lead Architect", "Security Officer",
    "Head of Operations", "Principal Engineer", "DevOps Lead",
    "Data Officer", "Compliance Manager"
]

EMAILS = [
    "akash@gmail.com", "john@yahoo.com", "sarah.k@company.io",
    "maria.dev@outlook.com", "david.ops@techcorp.com", "lisa@startup.co",
    "james.r@enterprise.net", "elena.m@corp.org", "raj.patel@firm.com",
    "priya.s@bigco.io", "m.chen@dataworks.ai", "a.garcia@cloudops.dev",
    "f.ahmed@securenet.com", "w.zhang@mlops.io", "n.volkov@infratech.co"
]

PHONES = [
    "9876543210", "9123456780", "8005551234", "9198765432",
    "7654321098", "8887776655", "9012345678", "8765432109",
    "7890123456", "9234567890"
]

API_KEYS = [
    "sk-1234567890abcd", "sk-abcdef1234567890",
    "sk-9f8e7d6c5b4a3210", "sk-a1b2c3d4e5f67890",
    "sk-deadbeef12345678", "sk-cafebabe87654321",
    "sk-0123456789abcdef", "sk-fedcba9876543210",
    "sk-1a2b3c4d5e6f7890", "sk-aabbccdd11223344"
]

NOISE = [
    "\n\nSent from iPhone",
    "\n---\nConfidential",
    "\n\nThanks!",
    "\n\nBest regards",
    "\n\n-- End of message --",
    "\n\nThis email is confidential. If you received it in error, please delete.",
    "\n\nDo not forward.",
    "",
    "\n\n[This message was auto-forwarded]",
    "\n\nPlease acknowledge receipt.",
]

TARGET_SAMPLES = 210  # Above the 200 minimum requirement

for i in range(TARGET_SAMPLES):
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
