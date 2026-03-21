def _render_movie_card(movie: dict) -> str:
    title = movie["title"]
    url = movie.get("imdb_url", "#")
    director = movie.get("director") or "Unknown"
    cast = ", ".join(movie.get("cast", []))
    genres = ", ".join(movie.get("genres", []))
    meta_parts = []
    runtime = movie.get("runtime")
    if runtime:
        meta_parts.append(f"{runtime} min")
    meta_parts.append(movie.get("mpaa_rating") or "Unrated")
    meta_line = " · ".join(meta_parts)

    rerelease = (
        ' <span style="background:#f9a825;color:#000;padding:2px 8px;border-radius:4px;'
        'font-size:12px;font-weight:bold">Re-release</span>'
        if movie.get("is_rerelease")
        else ""
    )

    return f"""
    <div style="border:1px solid #ddd;border-radius:8px;padding:16px;margin-bottom:16px;font-family:Arial,sans-serif">
      <div style="font-size:18px;font-weight:bold;margin-bottom:8px">
        <a href="{url}" style="color:#1a73e8;text-decoration:none">{title}</a>{rerelease}
      </div>
      {'<div style="color:#888;font-size:13px;margin-bottom:8px">' + meta_line + "</div>" if meta_line else ""}
      <div style="color:#555;font-size:14px;margin-bottom:4px"><strong>Director:</strong> {director}</div>
      <div style="color:#555;font-size:14px;margin-bottom:4px"><strong>Cast:</strong> {cast}</div>
      <div style="color:#555;font-size:14px"><strong>Genre:</strong> {genres}</div>
    </div>"""


def render_email(
    new_movies: list[dict],
    date: str,
) -> str:
    sections = []

    if not new_movies:
        sections.append('<p style="color:#555;font-size:16px">No new movies at Regal this week.</p>')
    else:
        for movie in new_movies:
            sections.append(_render_movie_card(movie))

    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="background:#f5f5f5;padding:24px">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;padding:32px">
    <h1 style="color:#222;font-family:Arial,sans-serif;margin-bottom:4px">New Movies at Regal</h1>
    <p style="color:#888;font-size:14px;margin-top:0;font-family:Arial,sans-serif">{date}</p>
    {body}
    <hr style="border:none;border-top:1px solid #eee;margin-top:32px">
    <p style="color:#aaa;font-size:11px;font-family:Arial,sans-serif;text-align:center">
      Powered by TMDB
    </p>
  </div>
</body>
</html>"""
