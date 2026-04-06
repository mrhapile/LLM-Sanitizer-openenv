import json


OVER_DELETION_MIN_RATIO = 0.3
BYPASS_INCORRECT_PENALTY = -1.0


def _normalized_len(text):
    # Treat repeated/leading/trailing whitespace as non-meaningful content.
    return len(" ".join((text or "").split()))


def _has_sensitive_targets(original_text, gold_entry):
    sensitive_items = [
        gold_entry["email"],
        gold_entry["api_key"],
        gold_entry["phone"],
    ]

    if any(item and item in original_text for item in sensitive_items):
        return True

    # Name-role linkage is considered sensitive only when both appear together.
    name = gold_entry["name"]
    role = gold_entry["role"]
    if name in original_text and role in original_text:
        return True

    return False

class VaultGrader:
    def __init__(self):
        with open("data/gold_manifest.json") as f:
            self.gold = json.load(f)

    def get_gold(self, idx):
        return self.gold[idx]

    def grade(self, original_text, agent_output, gold_entry, action_type="redact"):
        if action_type == "bypass":
            return 1.0 if not _has_sensitive_targets(original_text, gold_entry) else BYPASS_INCORRECT_PENALTY

        # Prevent reward exploitation via aggressive deletion of useful context.
        if original_text and _normalized_len(agent_output) < OVER_DELETION_MIN_RATIO * _normalized_len(original_text):
            return 0.0

        TP = 0
        FN = 0
        FP = 0

        # -------------------------
        # 1. Sensitive values
        # -------------------------
        sensitive_items = [
            gold_entry["email"],
            gold_entry["api_key"],
            gold_entry["phone"]
        ]

        # -------------------------
        # 2. Check removal
        # -------------------------
        for item in sensitive_items:
            if item in original_text:
                if item not in agent_output:
                    TP += 1   # correctly removed
                else:
                    FN += 1   # missed

        # -------------------------
        # 3. Entity relation (HARD TASK)
        # -------------------------
        name = gold_entry["name"]
        role = gold_entry["role"]

        if name in original_text and role in original_text:
            if name not in agent_output and role not in agent_output:
                TP += 1
            else:
                FN += 1

        # -------------------------
        # 4. Over-redaction check
        # -------------------------
        original_words = set(original_text.split())
        output_words = set(agent_output.split())

        removed_words = original_words - output_words

        allowed_removals = sensitive_items + [name, role]
        for word in removed_words:
            # Ignore punctuation-attached words if they contain allowed secrets
            if not any(allowed in word for allowed in allowed_removals if allowed):
                FP += 1

        # -------------------------
        # 5. Final score
        # -------------------------
        max_possible = sum(1 for item in sensitive_items if item in original_text)
        if name in original_text and role in original_text:
            max_possible += 1
            
        max_possible = max_possible or 1 # safety override
        raw_score = (TP * 1.0) - (FN * 1.0) - (FP * 0.5)

        score = raw_score / max_possible
        score = max(0.0, min(1.0, score))

        return score
