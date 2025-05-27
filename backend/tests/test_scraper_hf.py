from backend.src.scrapers.hf_open_llm import fetch

def test_scraper_hf_contract():
    data = fetch()
    assert isinstance(data, list)
    # For now, just check contract; real test will mock data
    for item in data:
        assert 'model_name' in item
        assert 'benchmark' in item
        assert 'metric' in item
        assert 'value' in item
        assert 'higher_is_better' in item 