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
    
    # Adicionando um User-Agent personalizado para evitar bloqueios de bots/CI
    headers = {"User-Agent": "bibliotheca-catalog-script/1.0"}

    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)

            # Tratando 429 e erros 50x (incluindo 503) com backoff exponencial
            if response.status_code in [429, 500, 502, 503, 504]:
                print(f"⚠️ Erro HTTP {response.status_code} no Google para o ISBN {isbn}. Aguardando {retry_delay}s...")
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
            
            # Aplica o delay caso ocorra exceção (ex: timeout de rede)
            time.sleep(retry_delay)
            retry_delay *= 2

    return None
