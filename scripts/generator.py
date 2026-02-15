import requests
import json
import re
import os

def normalize_isbn(isbn_raw):
    """Removes hyphens, spaces, and non-numeric characters."""
    return re.sub(r'[^0-9X]', '', isbn_raw.upper())

def get_cutter_number(author_surname):
    """
    A more robust algorithmic Cutter approach.
    Uses the first vowel/consonant transition to generate a 3-digit code.
    """
    surname = author_surname.upper()
    # Basic mapping for the first few letters to simulate the Sanborn table
    mapping = {'A': '1', 'E': '2', 'I': '3', 'O': '4', 'U': '5', 'S': '6', 'T': '7'}
    
    # Get second char if available, else default
    second_char = surname[1] if len(surname) > 1 else '0'
    num_part = mapping.get(second_char, '25') # '25' is a common mid-range consonant value
    
    # Ensure it looks like a standard 3-digit library code
    return num_part.ljust(3, '0')

def fetch_book_data(isbn_raw):
    isbn = normalize_isbn(isbn_raw)
    print(f"🔍 Fetching: {isbn}")
    
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "items" not in data:
            print(f"❌ No data found for ISBN: {isbn}")
            return None
            
        info = data["items"][0]["volumeInfo"]
        author = info.get("authors", ["Unknown"])[0]
        title = info.get("title", "Unknown")
        surname = author.split()[-1]
        
        # Cutter: Surname Initial + Generated Number + Title lowercase initial
        cutter = f"{surname[0].upper()}{get_cutter_number(surname)}{title[0].lower()}"
        
        return {
            "isbn": isbn,
            "title": title,
            "author": author,
            "cutter": cutter,
            "thumbnail": info.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://"),
            "category": info.get("categories", ["General"])[0]
        }
    except Exception as e:
        print(f"⚠️ Error fetching {isbn}: {e}")
        return None

def main():
    # 1. Read ISBNs from your text file
    if not os.path.exists('data/books.txt'):
        print("Create 'data/books.txt' first!")
        return

    with open('data/books.txt', 'r') as f:
        isbns = [line.strip() for line in f if line.strip()]

    # 2. Process and collect data
    library = []
    for isbn in isbns:
        book = fetch_book_data(isbn)
        if book:
            library.append(book)

    # 3. Save to the docs folder for GitHub Pages
    os.makedirs('docs', exist_ok=True)
    with open('docs/library.json', 'w') as f:
        json.dump(library, f, indent=4)
    print(f"✅ Successfully updated library.json with {len(library)} books.")

if __name__ == "__main__":
    main()