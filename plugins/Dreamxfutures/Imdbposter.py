import re
import aiohttp
import warnings
import logging
from io import BytesIO
from PIL import Image
from info import DREAMXBOTZ_IMAGE_FETCH, TMDB_API_KEY
from imdb import Cinemagoer


logger = logging.getLogger(__name__)
ia = Cinemagoer(accessSystem="https")
LONG_IMDB_DESCRIPTION = False

Image.MAX_IMAGE_PIXELS = None
warnings.simplefilter("ignore", Image.DecompressionBombWarning)

_session: aiohttp.ClientSession | None = None


async def get_session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def fetch_image(url, size=(860, 1200)):
    if not DREAMXBOTZ_IMAGE_FETCH:
        logger.info("Image fetching is disabled.")
        return url

    try:
        session = await get_session()

        async with session.get(url) as response:
            if response.status != 200:
                logger.error(f"Failed to fetch image: {response.status} for {url}")
                return None

            data = await response.read()
            img = Image.open(BytesIO(data))
            img = img.resize(size, Image.LANCZOS)

            out = BytesIO()
            img.save(out, format="JPEG")
            out.seek(0)
            return out

    except aiohttp.ClientError as e:
        logger.error(f"HTTP request error in fetch_image: {e}")
    except IOError as e:
        logger.error(f"I/O error in fetch_image: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in fetch_image: {e}")

    return None


async def close_session():
    global _session
    if _session and not _session.closed:
        await _session.close()

def list_to_str(lst):
    if lst:
        return ", ".join(map(str, lst))
    return ""

async def get_movie_details(query, id=False, file=None):
    try:
        if not id:
            query = query.strip().lower()
            title = query
            year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
            if year:
                year = list_to_str(year[:1])
                title = query.replace(year, "").strip()
            elif file is not None:
                year = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
                if year:
                    year = list_to_str(year[:1])
            else:
                year = None
            movieid = ia.search_movie(title.lower(), results=10)
            if not movieid:
                return None
            if year:
                filtered = list(filter(lambda k: str(k.get('year')) == str(year), movieid))
                if not filtered:
                    filtered = movieid
            else:
                filtered = movieid
            
            filtered_kind = list(filter(lambda k: k.get('kind') in ['movie', 'tv series'], filtered))
            if not filtered_kind:
                logger.info("No matches found for kind 'movie' or 'tv series', falling back to filtered list.")
                movieid = filtered
            else:
                movieid = filtered_kind
            
            movieid = movieid[0].movieID
        else:
            movieid = query
        movie = ia.get_movie(movieid)
        ia.update(movie, info=['main', 'vote details'])
        
        if movie.get("original air date"):
            date = movie["original air date"]
        elif movie.get("year"):
            date = movie.get("year")
        else:
            date = "N/A"
            
        plot = movie.get('plot')
        if plot and len(plot) > 0:
            plot = plot[0]
        else:
            plot = movie.get('plot outline')
        if plot and len(plot) > 800:
            plot = plot[:800] + "..."
            
        poster_url = movie.get('full-size cover url')
        return {
            'title': movie.get('title'),
            'votes': movie.get('votes'),
            "aka": list_to_str(movie.get("akas")),
            "seasons": movie.get("number of seasons"),
            "box_office": movie.get('box office'),
            'localized_title': movie.get('localized title'),
            'kind': movie.get("kind"),
            "imdb_id": f"tt{movie.get('imdbID')}",
            "cast": list_to_str(movie.get("cast")),
            "runtime": list_to_str(movie.get("runtimes")),
            "countries": list_to_str(movie.get("countries")),
            "certificates": list_to_str(movie.get("certificates")),
            "languages": list_to_str(movie.get("languages")),
            "director": list_to_str(movie.get("director")),
            "writer": list_to_str(movie.get("writer")),
            "producer": list_to_str(movie.get("producer")),
            "composer": list_to_str(movie.get("composer")),
            "cinematographer": list_to_str(movie.get("cinematographer")),
            "music_team": list_to_str(movie.get("music department")),
            "distributors": list_to_str(movie.get("distributors")),
            'release_date': date,
            'year': movie.get('year'),
            'genres': list_to_str(movie.get("genres")),
            'poster_url': poster_url + "._V1_SX1440.jpg" if poster_url.endswith("@.jpg") else poster_url,
            'plot': plot,
            'rating': str(movie.get("rating", "N/A")),
            'url': f'https://www.imdb.com/title/tt{movieid}'
        }
    except Exception as e:
        logger.exception(f"An error occurred in get_movie_details: {e}")
        return None

async def get_movie_detailsx(query, id=False, file=None):
    base_url = "https://bharath-boy-api.vercel.app/api/movie-posters"
    q = str(query).strip()
    try:
        async with aiohttp.ClientSession() as session:
            params = {"query": q, "api_key": TMDB_API_KEY}
            async with session.get(base_url, params=params) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"API request failed [{resp.status}] for query={q}\n {text}")
                    return await resp.json()
                
                data = await resp.json()
    except Exception as e:
        logger.error(f"An error occurred in get_movie_detailsx: {e}")
        return None

    # Normalize fields
    details = {}
    details['title'] = data.get('title') or data.get('localized_title')
    details['year'] = (data.get('year', 0)) if data.get('year') else None
    details['release_date'] = data.get('release_date')
    details['rating'] = round(float(data.get('rating', 0)), 1) if data.get('rating') is not None else None
    details['votes'] = int(data.get('votes', 0))
    details['runtime'] = data.get('runtime')
    details['certificates'] = data.get('certificates')
    details['tmdb_url'] = data.get('url')
    
    for key in ('genres', 'languages', 'countries'):
        raw = data.get(key)
        details[key] = [s.strip() for s in raw.split(',')] if raw else []
    for role in ('director', 'writer', 'producer', 'composer', 'cinematographer', 'cast'):
        raw = data.get(role)
        details[role] = [s.strip() for s in raw.split(',')] if raw else []
        
    details['plot'] = data.get('plot')
    details['tagline'] = data.get('tagline')
    details['box_office'] = (data.get('box_office', 0)) if data.get('box_office') else None
    raw_dist = data.get('distributors')
    details['distributors'] = [d.strip() for d in raw_dist.split(',')] if raw_dist else []
    details['imdb_id'] = data.get('imdb_id')
    details['tmdb_id'] = data.get('tmdb_id')
    
    posters = data.get('images', {}).get('posters', {})
    original_language = data.get('images', {}).get('original_language')
    poster_url = data.get('poster_url')
    if not poster_url:
        for key in ('en', original_language, 'xx'):
            if key and posters.get(key):
                poster_url = posters[key][0]
                break
    details['poster_url'] = poster_url.replace("/original/", "/w1280/") if poster_url else None

    backdrops = data.get('images', {}).get('backdrops', {})
    original_language = data.get('images', {}).get('original_language')
    backdrop_url = None
    for key in ('en', original_language, 'xx' or 'no_lang'):
        if key and backdrops.get(key):
            backdrop_url = backdrops[key][0]
            break
    details['backdrop_url'] = backdrop_url.replace("/original/", "/w1280/") if backdrop_url else None

    return details

