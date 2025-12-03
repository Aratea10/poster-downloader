import requests
import os
import sys
from typing import Optional
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)
else:
    exe_dir = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(exe_dir, ".env")
load_dotenv(env_path)

API_KEY = os.getenv("TMDB_API_KEY")

if not API_KEY:
    print("❌ No se encontró la API key.")
    print(f"   Asegúrate de que existe el archivo .env en: {exe_dir}")
    print("   Con el contenido: TMDB_API_KEY=tu_api_key")
    input("\nPulsa Enter para salir...")
    sys.exit(1)

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/original"


def search_media(title: str, media_type: str = "auto") -> Optional[dict]:
    """Busca película o serie en TMDB."""
    if media_type == "auto":
        movie = search_media(title, "movie")
        tv = search_media(title, "tv")
        if movie and tv:
            return (
                movie if movie.get("popularity", 0) >= tv.get("popularity", 0) else tv
            )
        return movie or tv
    endpoint = "search/movie" if media_type == "movie" else "search/tv"
    response = requests.get(
        f"{BASE_URL}/{endpoint}",
        params={"api_key": API_KEY, "query": title, "language": "es-ES"},
    ).json()
    if response.get("results"):
        result = response["results"][0]
        result["media_type"] = media_type
        return result
    return None


def get_poster_url(media_id: int, media_type: str) -> Optional[str]:
    """Obtiene la URL del poster con mayor resolución, priorizando España y luego US."""
    endpoint = f"movie/{media_id}" if media_type == "movie" else f"tv/{media_id}"
    images = requests.get(
        f"{BASE_URL}/{endpoint}/images",
        params={"api_key": API_KEY, "include_image_language": "es,en,null"},
    ).json()
    posters = images.get("posters", [])
    if not posters:
        return None

    for lang in ["es", "en", None]:
        lang_posters = [p for p in posters if p["iso_639_1"] == lang]
        if lang_posters:
            best_poster = max(lang_posters, key=lambda p: p.get("width", 0))
            return IMAGE_BASE + best_poster["file_path"]

    best_poster = max(posters, key=lambda p: p.get("width", 0))
    return IMAGE_BASE + best_poster["file_path"]


def download_poster(
    title: str, media_type: str = "auto", output_folder: str = "posters"
) -> Optional[str]:
    os.makedirs(output_folder, exist_ok=True)
    media = search_media(title, media_type)
    if not media:
        print(f"❌ No encontrado: {title}")
        return None
    media_title = media.get("title") or media.get("name")
    detected_type = media.get("media_type")
    tipo_str = "🎬" if detected_type == "movie" else "📺"
    poster_url = get_poster_url(media["id"], detected_type)
    if not poster_url:
        print(f"❌ Sin poster: {title}")
        return None
    response = requests.get(poster_url)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in media_title)
    filepath = os.path.join(output_folder, f"{safe_title}.jpg")
    with open(filepath, "wb") as f:
        f.write(response.content)
    print(f"✅ {tipo_str} {media_title} → {filepath}")
    return filepath


def download_batch(
    titles: list[str], media_type: str = "auto", output_folder: str = "posters"
):
    """Descarga posters en lote desde una lista."""
    print(f"📥 Descargando {len(titles)} títulos...\n")
    results = {"ok": [], "fail": []}
    for title in titles:
        path = download_poster(title, media_type, output_folder)
        if path:
            results["ok"].append(title)
        else:
            results["fail"].append(title)
    print(f"\n{'='*40}")
    print(f"✅ Descargados: {len(results['ok'])}")
    print(f"❌ Fallidos: {len(results['fail'])}")
    if results["fail"]:
        print(f"   → {', '.join(results['fail'])}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        arg = sys.argv[1]
    else:
        print("=" * 50)
        print("🎬 POSTER DOWNLOADER")
        print("=" * 50)
        print("\nOpciones:")
        print("  1. Escribe el título de una película/serie")
        print("  2. Escribe la ruta a un archivo .txt con títulos")
        print()
        arg = input("👉 Título o archivo: ").strip()

    if not arg:
        print("❌ No has introducido nada.")
        input("\nPulsa Enter para salir...")
        sys.exit(1)

    if arg.endswith(".txt"):
        try:
            with open(arg, "r", encoding="utf-8") as f:
                titles = [line.strip() for line in f if line.strip()]
            download_batch(titles)
        except FileNotFoundError:
            print(f"❌ No se encontró el archivo: {arg}")
    else:
        download_poster(arg)

    input("\nPulsa Enter para salir...")
