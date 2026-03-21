from filters import apply_pre_enrichment_filters, categorize_movie


def test_exclude_by_pattern():
    movies = [
        {"title": "Cool Action Movie", "showtime_count": 10},
        {"title": "Met Opera: La Bohème", "showtime_count": 2},
        {"title": "NT Live: Hamlet", "showtime_count": 1},
        {"title": "Fathom Events Special", "showtime_count": 3},
    ]
    patterns = ["Met Opera", "NT Live", "Bolshoi Ballet"]
    included, excluded = apply_pre_enrichment_filters(movies, patterns)
    assert len(included) == 2
    assert included[0]["title"] == "Cool Action Movie"
    assert included[1]["title"] == "Fathom Events Special"
    assert len(excluded) == 2


def test_exclude_fathom_in_title():
    movies = [
        {"title": "Fathom Events: Old Movie", "showtime_count": 5},
        {"title": "Regular Movie", "showtime_count": 8},
    ]
    patterns = ["Fathom"]
    included, excluded = apply_pre_enrichment_filters(movies, patterns)
    assert len(included) == 1
    assert included[0]["title"] == "Regular Movie"


def test_no_exclusions_when_empty_patterns():
    movies = [
        {"title": "Movie A", "showtime_count": 10},
        {"title": "Movie B", "showtime_count": 5},
    ]
    included, excluded = apply_pre_enrichment_filters(movies, [])
    assert len(included) == 2
    assert len(excluded) == 0


def test_categorize_new_movie():
    movie = {
        "title": "New Release",
        "showtime_count": 10,
        "release_date": "2026-03-14",
        "genres": ["Action"],
    }
    category = categorize_movie(movie, current_date="2026-03-20")
    assert category == "new"


def test_categorize_rerelease():
    movie = {
        "title": "Old Classic",
        "showtime_count": 8,
        "release_date": "2025-01-01",
        "genres": ["Drama"],
    }
    category = categorize_movie(movie, current_date="2026-03-20")
    assert category == "rerelease"


def test_categorize_music_is_new():
    movie = {
        "title": "Band Live",
        "showtime_count": 5,
        "release_date": "2026-03-14",
        "genres": ["Music"],
    }
    category = categorize_movie(movie, current_date="2026-03-20")
    assert category == "new"


def test_categorize_no_release_date():
    movie = {
        "title": "Mystery Movie",
        "showtime_count": 8,
        "release_date": None,
        "genres": ["Action"],
    }
    category = categorize_movie(movie, current_date="2026-03-20")
    assert category == "new"
