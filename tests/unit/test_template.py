from email_sender.template import render_email


def test_render_email_with_new_movies():
    new_movies = [
        {
            "title": "Action Hero",
            "imdb_url": "https://www.imdb.com/title/tt1234567/",
            "director": "Jane Smith",
            "cast": ["Actor A", "Actor B", "Actor C"],
            "genres": ["Action", "Adventure"],
            "is_rerelease": False,
        }
    ]
    html = render_email(new_movies=new_movies, date="March 20, 2026")
    assert "Action Hero" in html
    assert "https://www.imdb.com/title/tt1234567/" in html
    assert "Jane Smith" in html
    assert "Actor A" in html


def test_render_email_with_rerelease():
    new_movies = [
        {
            "title": "Old Classic",
            "imdb_url": "https://www.imdb.com/title/tt0000001/",
            "director": "Old Director",
            "cast": ["Classic Actor"],
            "genres": ["Drama"],
            "is_rerelease": True,
        }
    ]
    html = render_email(new_movies=new_movies, date="March 20, 2026")
    assert "Re-release" in html


def test_render_email_no_movies():
    html = render_email(new_movies=[], date="March 20, 2026")
    assert "No new movies" in html
