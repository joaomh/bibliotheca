import json
import os
import re
import time
import requests

def normalize_isbn(isbn_raw):
    return re.sub(r"[^0-9X]", "", str(isbn_raw).upper())

def get_cutter_number(author_surname):
    # ... (seu código original permanece igual)
    surname = author_surname.upper()
    mapping = {"A": "1", "E": "2", "I": "3", "O": "4", "U": "5", "S": "6", "T": "7"}
    second_char = surname[1] if len(surname) > 1 else "0"
    num_part = mapping.get(second_char, "25")
    return num_part.ljust(3, "0")

def fetch_book_data_mercadolivre(isbn):
    """Fallback 2: Busca na API pública do Mercado Livre (excelente para livros nacionais)."""
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={isbn}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            print(f"⚠️ ISBN {isbn} também não foi encontrado no Mercado Livre.")
            return None

        # Pega o primeiro resultado da busca
        item = data["results"][0]
        
        # O Mercado Livre costuma ter o nome do autor no título ou nos atributos
        title_raw = item.get("title", "Unknown")
        
        # Tenta extrair o autor dos atributos do produto, se existir
        author = "Unknown"
        attributes = item.get("attributes", [])
        for attr in attributes:
            if attr.get("id") == "AUTHOR":
                author = attr.get("value_name", "Unknown")
                break
        
        # Se não achou o autor, usa um genérico para o Cutter não quebrar
        surname = author.split()[-1] if author != "Unknown" else "Silva"
        
        # Limpeza básica do título (muitas vezes vem como "Livro - [Título]")
        title = re.sub(r"(?i)^livro\s*-\s*", "", title_raw)

        cutter = f"{surname[0].upper()}{get_cutter_number(surname)}{title[0].lower()}"

        # Melhoria da imagem: o thumbnail do ML geralmente termina em '-I.jpg'. 
        # Trocando por '-O.jpg' ou '-F.jpg' pegamos uma resolução melhor.
        thumbnail = item.get("thumbnail", "").replace("http://", "https://")
        thumbnail_high_res = thumbnail.replace("-I.jpg", "-O.jpg")

        print(f" -> [🟡 Sucesso via Mercado Livre API]")
        return {
            "isbn": isbn,
            "title": title[:50] + "..." if len(title) > 50 else title, # Evita títulos de anúncios gigantes
            "author": author,
            "cutter": cutter,
            "thumbnail": thumbnail_high_res,
            "category": "General", 
        }
    except Exception as e:
        print(f"❌ Erro ao consultar o Mercado Livre para o ISBN {isbn}: {e}")
        return None

def fetch_book_data_open_library(isbn):
    """Fallback 1: Busca na Open Library (Internet Archive)."""
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        key = f"ISBN:{isbn}"
        
        if key not in data:
            print(f"⚠️ ISBN {isbn} não encontrado na Open Library. Tentando Mercado Livre...")
            # PULA PARA O MERCADO LIVRE AQUI
            return fetch_book_data_mercadolivre(isbn)

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
        return fetch_book_data_mercadolivre(isbn)

def fetch_book_data(isbn_raw, api_key):
    # ... (seu código do google books permanece igual, chamando o fetch_book_data_open_library no final)
    # Exemplo do final do seu loop do Google Books:
    
            if "items" not in data:
                print(f"⚠️ ISBN {isbn} não encontrado no Google Books. Consultando Open Library...")
                return fetch_book_data_open_library(isbn)
                
    # ... (o resto permanece igual)
