import json
import os
import re
import time
import requests


def normalize_isbn(isbn_raw):
    return re.sub(r"[^0-9X]", "", str(isbn_raw).upper())


def get_cutter_number(author_surname):
    surname = author_surname.upper()
    mapping = {
        "A": "1",
        "E": "2",
        "I": "3",
        "O": "4",
        "U": "5",
        "S": "6",
        "T": "7",
    }
    second_char = surname[1] if len(surname) > 1 else "0"
    num_part = mapping.get(second_char, "25")
    return num_part.ljust(3, "0")


def fetch_book_data_open_library(isbn):
    """Fallback: Busca na Open Library (Internet Archive) se o livro não estiver no Google."""
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        key = f"ISBN:{isbn}"
        if key not in data:
            print(f"⚠️ ISBN {isbn} também não foi encontrado na Open Library.")
            return None

        info = data[key]
        title = info.get("title", "Unknown")

        # Trata a estrutura de autores da Open Library
        authors = info.get("authors", [])
        author = authors[0].get("name", "Unknown") if authors else "Unknown"
        surname = author.split()[-1] if author != "Unknown" else "Unknown"

        cutter = (
            f"{surname[0].upper()}{get_cutter_number(surname)}{title[0].lower()}"
        )

        # Recupera link da capa se disponível (tamanho médio)
        thumbnail = info.get("cover", {}).get("medium", "")

        print(f" -> [💡 Sucesso via Open Library]")
        return {
            "isbn": isbn,
            "title": title,
            "author": author,
            "cutter": cutter,
            "thumbnail": thumbnail,
            "category": "General",  # A Open Library usa assuntos muito heterogêneos, padronizamos em General
        }
    except Exception as e:
        print(f"❌ Erro ao consultar a Open Library para o ISBN {isbn}: {e}")
        return None


def fetch_book_data(isbn_raw, api_key):
    """Busca o livro no Google Books e aciona a Open Library como contingência."""
    isbn = normalize_isbn(isbn_raw)

    # 1. TENTATIVA PRINCIPAL: Google Books
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": f"isbn:{isbn}", "key": api_key}

    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)

            # Tratamento para limite de requisições (Rate Limiting)
            if response.status_code == 429:
                print(
                    f"⚠️ Erro 429 no Google para o ISBN {isbn}. Aguardando {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2
                continue

            response.raise_for_status()
            data = response.json()

            # Se NÃO achou os itens na base do Google, pula para a Open Library
            if "items" not in data:
                print(
                    f"⚠️ ISBN {isbn} não encontrado no Google Books. Consultando Open Library..."
                )
                return fetch_book_data_open_library(isbn)

            # Extração de dados padrão do Google Books
            info = data["items"][0]["volumeInfo"]
            author = info.get("authors", ["Unknown"])[0]
            title = info.get("title", "Unknown")
            surname = author.split()[-1]

            cutter = (
                f"{surname[0].upper()}{get_cutter_number(surname)}{title[0].lower()}"
            )

            time.sleep(
                1
            )  # Delay preventivo suave para evitar bloqueios futuros

            print(f" -> [🟢 Sucesso via Google Books]")
            return {
                "isbn": isbn,
                "title": title,
                "author": author,
                "cutter": cutter,
                "thumbnail": info.get("imageLinks", {})
                .get("thumbnail", "")
                .replace("http://", "https://"),
                "category": info.get("categories", ["General"])[0],
            }

        except requests.exceptions.RequestException as e:
            print(
                f"❌ Erro de conexão com o Google Books (Tentativa {attempt + 1}): {e}"
            )
            if attempt == max_retries - 1:
                print(
                    "⚠️ Falhas consecutivas no Google. Tentando Open Library como último recurso..."
                )
                return fetch_book_data_open_library(isbn)
            time.sleep(retry_delay)

    return None


def main():
    api_key = os.getenv("GOOGLE_BOOKS_API_KEY")

    if not api_key:
        print(
            "❌ Erro Crítico: A variável de ambiente GOOGLE_BOOKS_API_KEY não foi configurada."
        )
        return

    # 1. Carrega dados existentes da biblioteca
    library_path = "docs/library.json"
    existing_library = []
    existing_isbns = set()

    if os.path.exists(library_path):
        with open(library_path, "r", encoding="utf-8") as f:
            existing_library = json.load(f)
            existing_isbns = {
                normalize_isbn(book["isbn"]) for book in existing_library
            }

    # 2. Lê a lista de entrada de ISBNs
    if not os.path.exists("data/books.txt"):
        print("data/books.txt not found.")
        return

    with open("data/books.txt", "r") as f:
        new_isbns = [
            line.strip()
            for line in f
            if line.strip()
            and normalize_isbn(line.strip()) not in existing_isbns
        ]

    if not new_isbns:
        print("✨ No new ISBNs to add.")
        return

    # 3. Processa em cascata dupla os novos registros
    for isbn in new_isbns:
        print(f"🔍 Processing ISBN: {isbn}")
        book = fetch_book_data(isbn, api_key)
        if book:
            existing_library.append(book)
            print(f"📖 Added to catalog: '{book['title']}'")

    # 4. Salva o catálogo consolidado
    os.makedirs("docs", exist_ok=True)
    with open(library_path, "w", encoding="utf-8") as f:
        json.dump(existing_library, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Library updated. Total books in catalog: {len(existing_library)}")


if __name__ == "__main__":
    main()
