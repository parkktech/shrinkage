"""settings.load — defaults, partial-file merge, and the oracle switch."""
import json

import settings


def test_defaults_include_oracle_autoinstall_off(repo):
    d = settings.load(repo)
    assert d["oracle_autoinstall"] is False        # ask-first is the default


def test_partial_file_merges_over_defaults(repo):
    cfg = repo / ".claude"
    cfg.mkdir()
    (cfg / "shrinkage.json").write_text(json.dumps({"oracle_autoinstall": True}))
    d = settings.load(repo)
    assert d["oracle_autoinstall"] is True         # override honored
    assert d["gate"] == "soft"                      # untouched keys keep defaults


def test_corrupt_file_falls_back_to_defaults(repo):
    cfg = repo / ".claude"
    cfg.mkdir()
    (cfg / "shrinkage.json").write_text("{not json")
    d = settings.load(repo)
    assert d == settings.DEFAULTS
