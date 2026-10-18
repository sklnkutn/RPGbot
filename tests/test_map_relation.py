import pytest
from engine.map_relation_to_text import map_relation_to_text

@pytest.mark.parametrize("stat_name", ["trust", "respect", "affection", "fear", "annoyance", "jealousy"])
def test_zero_is_neutral(stat_name):
    result = map_relation_to_text(stat_name, 0)
    assert "нейтрал" in result.lower() or "безразлич" in result.lower() or "спокойств" in result.lower() or "нейтраль" in result.lower()

@pytest.mark.parametrize("value", [-100, -10, 0, 10, 100])
@pytest.mark.parametrize("stat_name", ["trust", "respect", "affection", "fear", "annoyance", "jealousy"])
def test_map_relation_bounds(stat_name, value):
    result = map_relation_to_text(stat_name, value)
    assert isinstance(result, str)
    assert len(result) > 0