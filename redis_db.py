# redis_db.py
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def _parse_anime(data):
    """Helper: converts stored string → proper types"""
    if not data:
        return None
    if 'genres' in data and data['genres']:
        data['genres'] = [g.strip() for g in data['genres'].split(',') if g.strip()]
    else:
        data['genres'] = []
    
    # Extract ID from key
    data['id'] = data.get('id') or ""
    return data

def get_all_anime():
    keys = r.keys("anime:*")
    anime_list = []
    for key in keys:
        raw = r.hgetall(key)
        if raw:
            anime = _parse_anime(raw)
            anime['id'] = key  # full key like "anime:12345"
            anime_list.append(anime)
    return anime_list

def get_distinct_genres():
    genres = set()
    for anime in get_all_anime():
        genres.update(anime.get('genres', []))
    return sorted(genres)

# NEW: Full search with title + genre + year range!
def search_anime(query="", genre="", year_from=None, year_to=None):
    """
    Search anime with optional filters.
    - query: string in title
    - genre: exact genre match (case insensitive)
    - year_from / year_to: int or None
    """
    results = []
    query = query.lower() if query else ""
    genre = genre.lower() if genre else ""

    for anime in get_all_anime():
        # Title match
        title = anime.get("title", "").lower()
        title_en = anime.get("title_english", "").lower()
        title_jp = anime.get("title_japanese", "").lower()
        if query and query not in title and query not in title_en and query not in title_jp:
            continue

        # Genre match
        anime_genres = [g.lower() for g in anime.get("genres", [])]
        if genre and genre not in anime_genres:
            continue

        # Year range match
        try:
            anime_year = int(anime.get("year")) if anime.get("year") else None
        except:
            anime_year = None

        if year_from and (anime_year is None or anime_year < year_from):
            continue
        if year_to and (anime_year is None or anime_year > year_to):
            continue

        results.append(anime)

    # Sort by title
    results.sort(key=lambda x: x.get("title", "").lower())
    return results


def update_anime(key, data):
    cleaned_data = {}
    for k, v in data.items():
        if v is None:
            cleaned_data[k] = "" 
        elif k == "genres" and isinstance(v, list):
            cleaned_data[k] = ",".join(v) 
        elif isinstance(v, (str, int, float)):
            cleaned_data[k] = str(v)
        else:
            cleaned_data[k] = str(v)
    if r.exists(key):
        r.hset(key, mapping=cleaned_data)
        return True
    return False
    
    
def delete_anime(anime_id):
    print(anime_id)
    return r.delete(anime_id) > 0
