from json import loads
from statistics import mean
import requests
import uuid

from flask import Flask, jsonify
import google.generativeai as genai
import os


class BooksCollection:
    BOOK_FIELDS = ["title", "authors", "ISBN", "publisher", "publishDate", "genre", "language", "summary", "id"]

    def __init__(self):
        self.db = {"books": [], "ratings": []}

    @staticmethod
    def validate_title(title):
        return isinstance(title, str) and not len(str)

    @staticmethod
    def validate_genre(genre):
        valid_genres = ["Fiction", "Children", "Biography", "Science", "Science Fiction", "Fantasy", "Other"]
        return genre in valid_genres

    def validate_isbn(self, isbn):
        return isinstance(isbn, str) and len(isbn) == 13 and not self.search_by_field("ISBN", isbn)

    @staticmethod
    def validate_data(title, genre, isbn):
        return BooksCollection.validate_title(title) and BooksCollection.validate_genre(
            genre) and BooksCollection().validate_isbn(isbn)

    def insert_book(self, title: str, isbn: str, genre: str):
        if not (BooksCollection.validate_data(title, isbn, genre)):
            return 422
        book_id = str(uuid.uuid4())  # TODO: Validate unique id?
        book_google_api_data, response_code = self.get_book_google_data(isbn)
        book_open_lib_api_data, response_code = self.get_book_open_lib_data(isbn)
        authors = publisher = published_date = language = "missing"
        if response_code == 200:
            authors = book_google_api_data["authors"][0] if len(book_google_api_data["authors"]) == 1 else \
                book_google_api_data["authors"]
            publisher = book_google_api_data["publisher"]
            published_date = book_google_api_data["publishedDate"]
            language = book_open_lib_api_data["language"]

        book = dict(title=title, authors=authors, ISBN=isbn, publisher=publisher, publishedDate=published_date,
                    genre=genre, language=language, summary=self.get_book_ai_info(title, authors), id=book_id)
        self.db["books"].append(book)
        self.db["ratings"].append({'values': [], 'average': 0, 'title': title, 'id': book_id})
        return 200

    def get_book(self, query: str):
        # if the query is empty then return all books
        if not query:
            return self.db["books"], 200
        # filter by "field"="value"
        elif "=" in query:
            field, value = query.split("=")
        # filter by "field" contains "value"
        elif "contains" in query:
            field, value = query.split(" contains ")
        else:
            return None, 422

        result = self.search_by_field(field, value)
        # if the {id} is not a recognized id
        if field == "id" and not result:
            return None, 404
        return result, 200

    def update_book(self, id_value: str, payload: str):
        try:
            dict = loads(payload)
        except:  # unsupported media type
            return None, 415

        # incorrect field names
        if not set(dict.keys()).issubset(set(BooksCollection.BOOK_FIELDS)):
            return None, 422

        # genre is not one of excepted values
        if "genre" in dict.keys() and not BooksCollection.validate_genre(dict["genre"]):
            return None, 422
        # TODO: validate the fields? ask Danny

        # find a book by payload in /books resource
        for book in self.db["books"]:
            if book["id"] == id_value:
                for field, value in dict.items():
                    book[field] = value
                return id_value, 201
        # id is not a recognized id
        return None, 404

    def delete_book(self, id_value: str):
        for idx, book in enumerate(self.db["books"]):
            if book["id"] == id_value:
                del self.db["books"][idx]
                return id_value, 200
        # id is not a recognized id
        return None, 404

    def rate_book(self, book_id: str, payload: str):
        try:
            dict = loads(payload)
        except:  # unsupported media type
            return None, 415

        rate = int(dict["value"])
        # invalid rating
        if rate not in [1, 2, 3, 4, 5]:
            return None, 422
        for rating in self.db["ratings"]:
            if rating["id"] == book_id:
                rating["values"].append(rate)
                rating["average"] = mean(rating["values"])
                return book_id, 200
        # id is not a recognized id
        return None, 404

    def get_book_ratings_by_id(self, book_id):
        for rating in self.db["ratings"]:
            if rating["id"] == book_id:
                return rating, 200
        return None, 422

    def get_book_ratings(self):
        return self.db["ratings"], 200

    def get_top(self):
        relevant_ratings = {rating["average"] for rating in self.db["ratings"] if len(rating["title"]) >= 3}
        top_ratings = sorted(relevant_ratings, reverse=True)[:3]
        top_books = {key: [] for key in top_ratings}
        for rating in self.db["ratings"]:
            # book must have at least 3 ratings
            if len(rating["values"]) < 3:
                continue
            if rating["average"] in top_books.keys():
                top_books[rating["average"]].append(rating)
        return top_books.values(), 200

    def search_by_field(self, field: str, value: str):
        ''' filter books by query parameter'''
        result = []
        if self.db["books"] and field not in self.db["books"][0]:
            return result
        for book in self.db["books"]:
            if isinstance(book[field], list):
                if value in book[field]:
                    result.append(book)
            elif value == book[field]:
                result.append(book)
        return result[0] if len == 1 else result

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
