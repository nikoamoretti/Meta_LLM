from backend.src.scoring.composite import category_composite, overall_composite

def test_category_composite():
    assert category_composite([1, 2, 3]) == 2.0

def test_overall_composite():
    assert overall_composite([2, 4]) == 3.0 