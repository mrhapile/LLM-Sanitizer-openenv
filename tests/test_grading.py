from grader.grading import parse_json_score, parse_kv_score, structure_score
from grader.normalization import compact_string, target_removed


def test_parse_json_score_requires_expected_keys():
    text = '{"service":"payments","owner_email":"[REDACTED]","on_call":"[REDACTED]","api_key":"[REDACTED]","status":"rotate"}'
    assert parse_json_score(text, ["service", "owner_email", "on_call", "api_key", "status"]) == 1.0


def test_parse_json_score_returns_zero_for_invalid_json():
    assert parse_json_score('{"service":"payments",}', ["service"]) == 0.0


def test_parse_kv_score_tracks_required_keys():
    text = "service: analytics\npager: [REDACTED]\nnotes: rotate"
    assert parse_kv_score(text, ["service", "pager", "notes"]) == 1.0
    assert parse_kv_score(text, ["service", "pager", "backup_email"]) < 1.0


def test_structure_score_falls_back_to_text_presence():
    assert structure_score("safe text", {"type": "text", "required_keys": []}) == 1.0
    assert structure_score("", {"type": "text", "required_keys": []}) == 0.0


def test_compact_matching_handles_obfuscated_secret():
    assert compact_string("s k - live - WARE - 5544 - 9911") == "skliveware55449911"
    assert target_removed("[REDACTED]", "sk-live-WARE-5544-9911", "compact") is True
    assert target_removed("s k - live - WARE - 5544 - 9911", "sk-live-WARE-5544-9911", "compact") is False
