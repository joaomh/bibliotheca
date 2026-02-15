# 📚 Bibliotheca

An automated personal library inventory system featuring **Cutter-Sanborn** classification and automated metadata enrichment.

## 🛠️ Project Overview
This repository serves as a cataloging engine that automates the organization of a physical book collection. By simply adding an ISBN to a list, the system fetches bibliographic data and generates a searchable, theme-grouped dashboard.

- **Metadata Extraction:** Fetches Author, Title, Category, and Thumbnails via the Google Books API.
- **Cutter-Sanborn Calculation:** Automatically generates alphanumeric codes to organize physical books by author and title sequence.
- **Automated Pipeline:** Uses GitHub Actions to process data and deploy the interface via GitHub Pages.
- **Theme Grouping:** A dynamic web dashboard that allows for searching and grouping books by subject (e.g., Physics, Computers, Science).

## 🚀 How to Add New Books
Adding to your library is fully automated through the following steps:

1. Open the file `data/books.txt`.
2. Append the **ISBN** of your book (hyphens or spaces are okay).
3. **Commit and Push** the changes to GitHub.
4. Wait ~2 minutes for the **GitHub Action** to:
   - Normalize the ISBN.
   - Fetch metadata and calculate the Cutter code.
   - Update the `library.json` database without duplicates.
   - Re-deploy the live dashboard.

## 🏗️ Technical Architecture
The project follows a modern JAMstack architecture:
- **Backend:** Python 3.x (Requests, Regex, JSON).
- **CI/CD:** GitHub Actions.
- **Frontend:** HTML5, Tailwind CSS, Lucide Icons.
- **Data Source:** Google Books API.


## 📂 Repository Structure
- `data/books.txt`: The input list of ISBNs.
- `scripts/generator.py`: The Python engine for data processing.
- `docs/`: The public-facing website and generated `library.json`.
- `.github/workflows/`: The automation instructions for GitHub.
