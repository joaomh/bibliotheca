import requests
import json

def get_cutter_number(author_surname):
    # Simplified Cutter-Sanborn Logic
    # In a full version, this would reference a lookup table
    mapping = {'A': '1', 'E': '2', 'I': '3', 'O': '4', 'U': '5', 'S': '6', 'T': '7'}
    char = author_surname[1].upper() if len(author_surname) > 1 else '0'
    return mapping.get(char, '2') # Defaulting to '2' for consonants

def fetch_book_data(isbn):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    response = requests.get(url).json()
    
    if "items" not in response:
        return None
        
    info = response["items"][0]["volumeInfo"]
    author = info.get("authors", ["Unknown"])[0]
    title = info.get("title", "Unknown")
    surname = author.split()[-1]
    
    # Generate Cutter: Author Initial + Table Num + First Letter of Title
    cutter = f"{surname[0].upper()}{get_cutter_number(surname)}{title[0].lower()}"
    
    return {
        "isbn": isbn,
        "title": title,
        "author": author,
        "cutter": cutter,
        "thumbnail": info.get("imageLinks", {}).get("thumbnail", ""),
        "category": info.get("categories", ["Uncategorized"])[0]
    }

# Logic to read books.txt and save to library.json would go here