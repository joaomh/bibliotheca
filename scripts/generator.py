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


def fetch_book_data(isbn_raw, api_key):
    isbn = normalize_isbn(isbn_raw)
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": f"isbn:{isbn}", "key": api_key}

    max_retries = 5
    retry_delay = 2  # Tempo inicial de espera em segundos para o erro 429

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)

            # Tratamento específico para Rate Limiting (Erro 429)
            if response.status_code == 429:
                print(
                    f"⚠️ Erro 429 no ISBN {isbn}. Tentativa {attempt + 1}/{max_retries}. Aguardando {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Dobra o tempo (2s, 4s, 8s, 16s...)
                continue

            response.raise_for_status()
            data = response.json()

            if "items" not in data:
                print(f"⚠️ ISBN {isbn} not found in Google Books.")
                return None

            info = data["items"][0]["volumeInfo"]
            author = info.get("authors", ["Unknown"])[0]
            title = info.get("title", "Unknown")
            surname = author.split()[-1]

            cutter = (
                f"{surname[0].upper()}{get_cutter_number(surname)}{title[0].lower()}"
            )

            # Delay preventivo sutil entre requisições bem-sucedidas
            time.sleep(1)

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
            print(f"❌ Error fetching {isbn} (Attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                return None
            time.sleep(retry_delay)

    return None


def main():
    api_key = os.getenv("GOOGLE_BOOKS_API_KEY")

    if not api_key:
        print(
            "❌ Erro Crítico: A variável de ambiente GOOGLE_BOOKS_API_KEY não foi configurada."
        )
        return

    # 1. Load existing library data if it exists
    library_path = "docs/library.json"
    existing_library = []
    existing_isbns = set()

    if os.path.exists(library_path):
        with open(library_path, "r", encoding="utf-8") as f:
            existing_library = json.load(f)
            existing_isbns = {
                normalize_isbn(book["isbn"]) for book in existing_library
            }

    # 2. Read ISBNs from books.txt
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

    # 3. Fetch only the NEW books and append them
    for isbn in new_isbns:
        print(f"🔍 Fetching: {isbn}...")
        book = fetch_book_data(isbn, api_key)
        if book:
            existing_library.append(book)
            print(f"📖 Added: {book['title']}")

    # 4. Save the merged list back to docs/
    os.makedirs("docs", exist_ok=True)
    with open(library_path, "w", encoding="utf-8") as f:
        json.dump(existing_library, f, indent=4, ensure_ascii=False)

    print(f"✅ Library updated. Total books: {len(existing_library)}")


if __name__ == "__main__":
    main()