import requests
import os
import sys
from typing import Optional
from dotenv import load_dotenv

if getattr(sys, "frozen", False):
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


def search_media(
    title: str, media_type: str = "auto", interactive: bool = True
) -> Optional[dict]:
    if media_type == "auto":
        all_results = []

        for mtype in ["movie", "tv"]:
            endpoint = f"search/{mtype}"
            response = requests.get(
                f"{BASE_URL}/{endpoint}",
                params={"api_key": API_KEY, "query": title, "language": "es-ES"},
            ).json()

            if response.get("results"):
                for result in response["results"][:5]:  # Máximo 5 por tipo
                    result["media_type"] = mtype
                    all_results.append(result)

        if not all_results:
            return None

        if len(all_results) == 1:
            return all_results[0]

        if interactive:
            print(f"\n🔍 Encontrados {len(all_results)} resultados para '{title}':")
            print("=" * 50)

            for idx, result in enumerate(all_results, 1):
                result_title = result.get("title") or result.get("name")
                year = ""
                if result.get("release_date"):
                    year = f" ({result['release_date'][:4]})"
                elif result.get("first_air_date"):
                    year = f" ({result['first_air_date'][:4]})"

                tipo = "🎬 Película" if result["media_type"] == "movie" else "📺 Serie"
                print(f"  {idx}. {result_title}{year} - {tipo}")

            print("\n👉 Elige el número (o Enter para el primero): ", end="")
            choice = input().strip()

            if choice == "":
                return all_results[0]

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(all_results):
                    return all_results[idx]
                else:
                    print("⚠️  Número inválido, seleccionando el primero...")
                    return all_results[0]
            except ValueError:
                print("⚠️  Entrada inválida, seleccionando el primero...")
                return all_results[0]
        else:
            return max(all_results, key=lambda x: x.get("popularity", 0))

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
    """Obtiene la URL del poster con mayor resolución de US"""
    endpoint = f"movie/{media_id}" if media_type == "movie" else f"tv/{media_id}"
    images = requests.get(
        f"{BASE_URL}/{endpoint}/images",
        params={"api_key": API_KEY, "include_image_language": "en"},
    ).json()
    posters = images.get("posters", [])
    if not posters:
        return None

    en_posters = [p for p in posters if p["iso_639_1"] == "en"]
    if en_posters:
        best_poster = max(en_posters, key=lambda p: p.get("width", 0))
        return IMAGE_BASE + best_poster["file_path"]

    best_poster = max(posters, key=lambda p: p.get("width", 0))
    return IMAGE_BASE + best_poster["file_path"]


def download_poster(
    title: str,
    media_type: str = "auto",
    output_folder: str = "posters",
    interactive: bool = True,
) -> Optional[str]:
    os.makedirs(output_folder, exist_ok=True)
    media = search_media(title, media_type, interactive=interactive)
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
    print(f"📥 Descargando {len(titles)} títulos...\n")
    results = {"ok": [], "fail": []}
    for title in titles:
        path = download_poster(title, media_type, output_folder, interactive=False)
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
        download_poster(arg, interactive=True)

    input("\nPulsa Enter para salir...")
