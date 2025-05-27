from backend.src.scoring.normalise import z_score

def test_z_score_higher():
    assert z_score(110, 100, 10, True) == 1.0

def test_z_score_lower():
    assert z_score(90, 100, 10, False) == 1.0 