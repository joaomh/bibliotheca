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
        "A": "1", "E": "2", "I": "3", "O": "4", "U": "5", "S": "6", "T": "7"
    }
    second_char = surname[1] if len(surname) > 1 else "0"
    num_part = mapping.get(second_char, "25")
    return num_part.ljust(3, "0")

def check_local_override(isbn):
    """Camada 1: Verifica se o livro foi cadastrado manualmente no JSON local."""
    manual_path = "data/manual_catalog.json"
    
    if os.path.exists(manual_path):
        with open(manual_path, "r", encoding="utf-8") as f:
            try:
                manual_data = json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Erro ao ler manual_catalog.json. Verifique o formato JSON.")
                return None
            
            # Procura o ISBN na lista manual
            for book in manual_data:
                if normalize_isbn(book.get("isbn", "")) == isbn:
                    
                    # Se houver foto local, substitui o thumbnail
                    cover_path = f"data/covers/{isbn}.jpg"
                    if os.path.exists(cover_path):
                        book["thumbnail"] = cover_path
                    
                    print(f" -> [📸 Sucesso via Catálogo Manual Local]")
                    return book
    return None

def fetch_book_data_open_library(isbn):
    """Camada 3 (Fallback): Busca na Open Library se não estiver no Google."""
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

        authors = info.get("authors", [])
        author = authors[0].get("name", "Unknown") if authors else "Unknown"
        surname = author.split()[-1] if author != "Unknown" else "Unknown"

        cutter = f"{surname[0].upper()}{get_cutter_number(surname)}{title[0].lower()}"
        thumbnail = info.get("cover", {}).get("medium", "")

        print(f" -> [💡 Sucesso via Open Library]")
        return {
            "isbn": isbn,
            "title": title,
            "author": author,
            "cutter": cutter,
            "thumbnail": thumbnail,
            "category": "General", 
        }
    except Exception as e:
        print(f"❌ Erro ao consultar a Open Library para o ISBN {isbn}: {e}")
        return None

def fetch_book_data(isbn_raw, api_key):
    """Busca o livro (1º Local, 2º Google Books, 3º Open Library)."""
    isbn = normalize_isbn(isbn_raw)

    # 1. TENTATIVA LOCAL (Manual Override)
    local_book = check_local_override(isbn)
    if local_book:
        return local_book

    # 2. TENTATIVA PRINCIPAL: Google Books
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": f"isbn:{isbn}", "key": api_key}

    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 429:
                print(f"⚠️ Erro 429 no Google para o ISBN {isbn}. Aguardando {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue

            response.raise_for_status()
            data = response.json()

            # Se NÃO achou no Google, pula para a Open Library
            if "items" not in data:
                print(f"⚠️ ISBN {isbn} não encontrado no Google Books. Consultando Open Library...")
                return fetch_book_data_open_library(isbn)

            info = data["items"][0]["volumeInfo"]
            author = info.get("authors", ["Unknown"])[0]
            title = info.get("title", "Unknown")
            surname = author.split()[-1]

            cutter = f"{surname[0].upper()}{get_cutter_number(surname)}{title[0].lower()}"

            time.sleep(1) 

            print(f" -> [🟢 Sucesso via Google Books]")
            return {
                "isbn": isbn,
                "title": title,
                "author": author,
                "cutter": cutter,
                "thumbnail": info.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://"),
                "category": info.get("categories", ["General"])[0],
            }

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão com o Google Books (Tentativa {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                print("⚠️ Falhas consecutivas no Google. Tentando Open Library como último recurso...")
                return fetch_book_data_open_library(isbn)
            time.sleep(retry_delay)

    return None

def main():
    api_key = os.getenv("GOOGLE_BOOKS_API_KEY")

    if not api_key:
        print("❌ Erro Crítico: A variável de ambiente GOOGLE_BOOKS_API_KEY não foi configurada.")
        return

    # Garante que os diretórios existam
    os.makedirs("docs", exist_ok=True)
    os.makedirs("data/covers", exist_ok=True) # Pasta para as fotos manuais

    # Carrega catálogo principal
    library_path = "docs/library.json"
    existing_library = []
    existing_isbns = set()

    if os.path.exists(library_path):
        with open(library_path, "r", encoding="utf-8") as f:
            existing_library = json.load(f)
            existing_isbns = {normalize_isbn(book["isbn"]) for book in existing_library}

    # Lê lista de entrada
    if not os.path.exists("data/books.txt"):
        print("❌ data/books.txt not found.")
        return

    with open("data/books.txt", "r") as f:
        new_isbns = [
            line.strip()
            for line in f
            if line.strip() and normalize_isbn(line.strip()) not in existing_isbns
        ]

    if not new_isbns:
        print("✨ Nenhum novo ISBN para adicionar.")
        return

    # Processa os registros
    for isbn in new_isbns:
        print(f"🔍 Processando ISBN: {isbn}")
        book = fetch_book_data(isbn, api_key)
        if book:
            existing_library.append(book)
            print(f"📖 Adicionado ao catálogo: '{book['title']}'")

    # Salva
    with open(library_path, "w", encoding="utf-8") as f:
        json.dump(existing_library, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Biblioteca atualizada. Total de livros no catálogo: {len(existing_library)}")

if __name__ == "__main__":
    main()
