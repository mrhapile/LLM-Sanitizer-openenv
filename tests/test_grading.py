from grader.grading import parse_json_score, parse_kv_score, structure_score


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
