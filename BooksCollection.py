import requests
import uuid

from flask import Flask, jsonify
import google.generativeai as genai
import os


class BooksCollection:

    def __init__(self):
        self.db = {"books": [], "ratings": []}

    def insert_book(self, title: str, isbn: str, genre: str):
        book_id = str(uuid.uuid4())  # TODO: Validate unique id?
        book_google_api_data, response_code = self.get_book_google_data(isbn)
        book_open_lib_api_data, response_code = self.get_book_open_lib_data(isbn)
        authors = publisher = published_date = language = "missing"
        if response_code == 200:
            authors = book_google_api_data["authors"][0] if len(book_google_api_data["authors"]) == 1 else book_google_api_data["authors"]
            publisher = book_google_api_data["publisher"]
            published_date = book_google_api_data["publishedDate"]
            language = book_open_lib_api_data["language"]

        book = dict(title=title, authors=authors, ISBN=isbn, publisher=publisher, publishedDate=published_date,
                    genre=genre, language=language, summary=self.get_book_ai_info(title, authors), id=book_id)
        self.db["books"].append(book)
        self.db["ratings"].append({'values': [], 'average': 0, 'title': title, 'id': book_id})

    def get_book(self, query:str):
        field, value = query.split("=")
        result = []
        if self.db["books"] and field not in self.db["books"][0]:
            return result
        for book in self.db["books"]:
            if isinstance(book[field], list):
                if value in book[field]:
                    result.append(book)
            elif value == book[field]:
                result.append(book)
        return result

    def update_book(self):
        pass

    def delete_book(self):
        pass

    def rate_book(self, book_id, rate):
        pass

    def get_book_ratings(self, book_id):
        pass

    def get_top(self):
        pass

    @staticmethod
    def get_book_google_data(isbn: str):
        google_books_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        try:
            response = requests.get(google_books_url)
            if response.json()['totalItems'] == 0:
                return jsonify({"error": "no items returned from Google Books API for given ISBN number"}), 400
            else:
                google_books_data = response.json()['items'][0]['volumeInfo']
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}, 400

        book_google_api_data = {
            "authors": google_books_data.get("authors"),
            "publisher": google_books_data.get("publisher"),
            "publishedDate": google_books_data.get("publishedDate")
        }
        return book_google_api_data, 200

    @staticmethod
    def get_book_open_lib_data(isbn: str):
        """
        gets the book language
        """
        open_lib_books_url = f"https://openlibrary.org/search.json?q={isbn}&fields=language"
        try:
            response = requests.get(open_lib_books_url)
            if response.json()['numFound'] == 0:
                return jsonify({"error": "no items returned from Open Library API for given ISBN number"}), 400
            else:
                open_lib_books_url = response.json()['docs'][0]
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}, 400

        book_google_api_data = {
            "language": open_lib_books_url.get("language"),
        }
        return book_google_api_data, 200

    @staticmethod
    def get_book_ai_info(title: str, author: str):
        api_key = 'AIzaSyAPaNhG9Yt76KmGBKq1JTF4c_iD4qZcfWM'
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(f"Summarize the book {title} by {author} in 5 sentences or less.")
        return response.text


if __name__ == '__main__':
    app = Flask(__name__)
    with app.app_context():
        book = BooksCollection()
        # print(book.get_book_google_data("9781408855652"))
        # print(book.get_book_open_lib_data("9781408855652"))  # Harry Potter
        # print(book.get_book_ai_info("Harry Potter and the Philosopher's Stone", "J. K. Rowling"))
        book.insert_book("Harry Potter and the Philosopher's Stone", "9781408855652", "Fantasy")
        print(book.get_book("genre=Fantasy"))
        print(book.get_book("language=eng"))
        # print(book.get_book("genre=Fantasy"))
