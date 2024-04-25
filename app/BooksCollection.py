from itertools import chain
from json import loads
from statistics import mean
import requests
import uuid
import re
from flask import Flask, jsonify
import google.generativeai as genai
import os


class BooksCollection:
    BOOK_FIELDS = ["title", "authors", "ISBN", "publisher", "publishDate", "genre", "language", "summary", "id"]

    def __init__(self):
        self.db = {"books": [], "ratings": []}

    @staticmethod
    def validate_title(title):
        # validate that title is type of string and not and empty string
        return isinstance(title, str) and len(title) > 0

    @staticmethod
    def validate_genre(genre):
        valid_genres = ["Fiction", "Children", "Biography", "Science", "Science Fiction", "Fantasy", "Other"]
        return genre in valid_genres

    @staticmethod
    def validate_publish_date(date):
        # Regular expression pattern for the format yyyy-mm-dd or yyyy
        pattern = r'^\d{4}(-\d{2}-\d{2})?$'

        # Check if the string matches the pattern
        if re.match(pattern, date):
            return True
        else:
            return False

    def validate_isbn(self, isbn):
        return isinstance(isbn, str) and len(isbn) == 13 and not self.search_by_field("ISBN", isbn)

    def validate_data(self, title, isbn, genre):
        return BooksCollection.validate_title(title) and BooksCollection.validate_genre(
            genre) and self.validate_isbn(isbn)

    def insert_book(self, title: str, isbn: str, genre: str):
        if not (self.validate_data(title, isbn, genre)):
            return None, 422
        book_id = str(uuid.uuid4())  # TODO: Validate unique id?
        book_google_api_data, response_code = self.get_book_google_data(isbn)
        book_open_lib_api_data, response_code = self.get_book_open_lib_data(isbn)
        authors = publisher = published_date = language = "missing"
        if response_code == 200:
            # handles the case that there is more than one author
            authors = " and ".join(book_google_api_data["authors"])
            publisher = book_google_api_data["publisher"]
            # validate that published date is in the correct format, else define "missing"
            published_date_str = book_google_api_data["publishedDate"]
            published_date = published_date_str if BooksCollection.validate_publish_date(published_date_str) else published_date
            language = book_open_lib_api_data["language"]

        book = dict(title=title, authors=authors, ISBN=isbn, publisher=publisher, publishedDate=published_date,
                    genre=genre, language=language, summary=self.get_book_ai_info(title, authors), id=book_id)
        self.db["books"].append(book)
        self.db["ratings"].append({'values': [], 'average': 0, 'title': title, 'id': book_id})
        return book_id, 201

    def get_book(self, query: dict):
        # TODO: check about "contains" query
        # if the query is empty then return all books
        if not query:
            return self.db["books"], 200

        filtered_books = self.db["books"]
        for key, value in query.items():
            if ' contains ' in key:
                field, value = key.split(' contains ')
                filtered_books = [book for book in filtered_books if value in book.get(field, '')]
            else:
                filtered_books = [book for book in filtered_books if book.get(key) == value]

            if not filtered_books:  # If no books match the criteria, stop searching
                return [], 200
        return filtered_books, 200

    def get_book_by_id(self, id: str):
        filtered_books = self.db["books"]
        result = self.search_by_field("id", id)
        # if the {id} is not a recognized id
        if not result:
            return None, 404
        return result, 200

    def update_book(self, put_values: dict):
        id_value = put_values["id"]
        # genre is not one of excepted values
        if not BooksCollection.validate_genre(put_values["genre"]):
            return None, 422
        # find a book by payload in /books resource
        for book in self.db["books"]:
            if book["id"] == id_value:
                for field, value in put_values.items():
                    book[field] = value
                return id_value, 200
        # id is not a recognized id
        return None, 404

    def delete_book(self, id_value: str):
        for idx, book in enumerate(self.db["books"]):
            if book["id"] == id_value:
                del self.db["books"][idx]
                return id_value, 200
        # id is not a recognized id
        return None, 404

    def rate_book(self, book_id: str, rate):
        # invalid rating
        if not float(int(rate)) == rate or int(rate) not in [1, 2, 3, 4, 5]:
            return None, None, 422
        for rating in self.db["ratings"]:
            if rating["id"] == book_id:
                rating["values"].append(rate)
                rating["average"] = mean(rating["values"])
                return book_id, rating["average"], 201
        # id is not a recognized id
        return None, None, 404

    def get_book_ratings_by_id(self, book_id):
        for rating in self.db["ratings"]:
            if rating["id"] == book_id:
                return rating, 200
        return None, 404

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
        return  list(chain.from_iterable(top_books.values())), 200

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
