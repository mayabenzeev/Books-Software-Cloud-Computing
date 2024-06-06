import json
from itertools import chain
from statistics import mean
import requests
import uuid
import re
import google.generativeai as genai


class BooksCollection:
    """
    A collection class for managing books and their ratings, leveraging external API data for enrichment.
    """

    BOOK_FIELDS = ["title", "authors", "ISBN", "publisher", "publishDate", "genre", "language", "summary", "id"]

    def __init__(self):
        self.db = {"books": [], "ratings": []}
        self.api_key = self.get_ai_api_key()  # Load API key on initialization

    @staticmethod
    def validate_title(title):
        """
        Validate that the title is a string and not empty.

        Args:
            title (str): The title of the book to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        return isinstance(title, str) and len(title) > 0

    @staticmethod
    def validate_genre(genre):
        """
        Validate genre against a preset list of valid genres.

        Args:
            genre (str): The genre to validate.

        Returns:
            bool: True if the genre is valid, False otherwise.
        """
        valid_genres = ["Fiction", "Children", "Biography", "Science", "Science Fiction", "Fantasy", "Other"]
        return genre in valid_genres

    @staticmethod
    def validate_publish_date(date):
        """
        Validate publish date against the pattern yyyy-mm-dd or yyyy.

        Args:
            date (str): The publishing date string to validate.

        Returns:
            bool: True if the date matches the pattern, False otherwise.
        """
        pattern = r'^\d{4}(-\d{2}-\d{2})?$'  # pattern for the format yyyy-mm-dd or yyyy
        return bool(re.match(pattern, date))  # Return if the string matches the pattern

    def validate_isbn(self, isbn):
        """
        Validate that the ISBN is exactly 13 characters long and unique within the database.

        Args:
            isbn (str): The ISBN to validate.

        Returns:
            bool: True if the ISBN is valid and unique, False otherwise.
        """
        return isinstance(isbn, str) and len(isbn) == 13 and not self.search_by_field("ISBN", isbn)

    def validate_data(self, title, isbn, genre):
        """
        Validate the title, ISBN, and genre for a new book.

        Args:
            title (str): The title to validate.
            isbn (str): The ISBN to validate.
            genre (str): The genre to validate.

        Returns:
            bool: True if all validations pass, False otherwise.
        """
        return BooksCollection.validate_title(title) and BooksCollection.validate_genre(
            genre) and self.validate_isbn(isbn)

    def insert_book(self, title: str, isbn: str, genre: str):
        """
        Insert a new book into the database if it passes validation.

        Args:
            title (str): The title of the book.
            isbn (str): The ISBN of the book.
            genre (str): The genre of the book.

        Returns:
            tuple: A tuple containing the book ID and response status code.
        """
        if not (self.validate_data(title, isbn, genre)):
            return None, 422

        book_id = str(uuid.uuid4())
        book_google_api_data, response_code = self.get_book_google_data(isbn)
        book_open_lib_api_data, response_code = self.get_book_open_lib_data(isbn)
        authors = publisher = published_date = language = "missing"

        if response_code == 200:
            # handles the case that there is more than one author
            authors = " and ".join(book_google_api_data["authors"])
            publisher = book_google_api_data["publisher"]
            # validate that published date is in the correct format, else define "missing"
            published_date_str = book_google_api_data["publishedDate"]
            published_date = published_date_str if BooksCollection.validate_publish_date(published_date_str) else (
                published_date)
            language = book_open_lib_api_data["language"]

        book = dict(title=title, authors=authors, ISBN=isbn, publisher=publisher, publishedDate=published_date,
                    genre=genre, language=language, summary=self.get_book_ai_info(title, authors), id=book_id)
        self.db["books"].append(book)
        self.db["ratings"].append({'values': [], 'average': 0, 'title': title, 'id': book_id})
        return book_id, 201

    def get_book(self, query: dict):
        """
        Retrieve books that match the specified query parameters.

        Args:
            query (dict): Query parameters for book search.

        Returns:
            tuple: A tuple of the filtered book list and response status code.
        """
        # If not specified, return all books data
        if not query:
            return self.db["books"], 200

        filtered_books = self.db["books"]
        for field, value in query.items():
            # String query has uncorrected field names. bad request
            if field not in self.BOOK_FIELDS:
                return None, 422

            # Genre in String query is an unsupported genre
            if field == "genre" and not self.validate_genre(value):
                return None, 422

            if field == "language":
                filtered_books = [book for book in filtered_books if value in book.get(field, '')]
            else:
                filtered_books = [book for book in filtered_books if book.get(field) == value]

            if not filtered_books:  # If no books match the criteria, stop searching
                return [], 200
        return filtered_books, 200

    def get_book_by_id(self, book_id: str):
        """
        Retrieve a book by its unique ID.

        Args:
            book_id (str): The unique identifier of the book in the db.

        Returns:
            tuple: A tuple containing the book or None if not found, and the response status code.
        """
        result = self.search_by_field("id", book_id)
        # if the {id} is not a recognized id
        if not result:
            return None, 404
        return result[0], 200

    def update_book(self, put_values: dict):
        """
       Update the details of an existing book based on provided values.

       Args:
           put_values (dict): A dictionary containing all fields to update.

       Returns:
           tuple: A tuple containing the updated book ID if successful, None if not, and the response status code.
       """
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

    def delete_book(self, book_id: str):
        """
        Delete a book from the database by its ID.

        Args:
            book_id (str): The unique identifier of the book to delete in the db.

        Returns:
            tuple: A tuple containing the ID of the deleted book if successful,
            None if not, and the response status code.
        """
        for idx, book in enumerate(self.db["books"]):
            if book["id"] == book_id:
                del self.db["books"][idx]
                return book_id, 200
        # id is not a recognized id
        return None, 404

    def rate_book(self, book_id: str, rate: int):
        """
        Add a rating to a book and update its average rating.

        Args:
            book_id (str): The ID of the book to rate in the db.
            rate (int): The rating value, must be an integer between 1 and 5.

        Returns:
            tuple: A tuple containing the book ID, the new average rating if successful,
            or None if not, and the response status code.
        """
        if not float(int(rate)) == rate or int(rate) not in [1, 2, 3, 4, 5]:  # invalid rating
            return None, None, 422

        for rating in self.db["ratings"]:
            if rating["id"] == book_id:
                rating["values"].append(rate)
                rating["average"] = mean(rating["values"])
                return book_id, rating["average"], 201

        return None, None, 404  # id is not a recognized id

    def get_book_ratings_by_id(self, book_id: str):
        """
        Retrieve the ratings for a specific book by its ID in the db.

        Args:
            book_id (str): The ID of the book in the db whose ratings are to be retrieved.

        Returns:
            tuple: A tuple containing the ratings if found, None if not, and the response status code.
        """
        for rating in self.db["ratings"]:
            if rating["id"] == book_id:
                return rating, 200
        return None, 404

    def get_book_ratings(self, query: dict):
        """
        Retrieve the ratings for all books.

        Returns:
            tuple: A tuple containing all ratings and the response status code.
        """
        # If not specified, return all ratings data
        if not query:
            return self.db["ratings"], 200

        filtered_ratings = self.db["ratings"]
        for field, value in query.items():
            # String query has uncorrected field names. bad request
            if field not in self.BOOK_FIELDS:
                return None, 422

            # Genre in String query is an unsupported genre
            if field == "genre" and not self.validate_genre(value):
                return None, 422

            if field == "language":
                filtered_ratings = [rate for rate in filtered_ratings if value in rate.get(field, '')]
            else:
                filtered_ratings = [rate for rate in filtered_ratings if rate.get(field) == value]

            if not filtered_ratings:  # If no books match the criteria, stop searching
                return [], 200
        return filtered_ratings, 200



    def get_top(self):
        """
        Retrieve the top three books with the highest average ratings that have at least three ratings.

        Returns:
            tuple: A tuple containing the list of top-rated books and the response status code.
        """
        # All books that has at least 3 rates
        relevant_ratings = {rating["average"] for rating in self.db["ratings"] if len(rating["title"]) >= 3}
        # Top 3 rating average sorted
        top_ratings = sorted(relevant_ratings, reverse=True)[:3]
        top_books = {key: [] for key in top_ratings}
        # Create a dictionary {rate_avg: [books]}
        for rating in self.db["ratings"]:
            # book must have at least 3 ratings
            if len(rating["values"]) < 3:
                continue
            if rating["average"] in top_books.keys():
                top_books[rating["average"]].append(rating)
        return list(chain.from_iterable(top_books.values())), 200

    def search_by_field(self, field: str, value: str):
        """
        Helper function: Search for books in the db by a specific field and value.

        Args:
            field (str): The field to search by.
            value (str): The value to search for.

        Returns:
            list: A list of books that match the search criteria.
        """
        result = []
        if self.db["books"] and field not in self.db["books"][0]:  # Empty db or uncorrected field name
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
        """
        Fetch book data from Google Books API using the ISBN.

        Args:
            isbn (str): The ISBN of the book.

        Returns:
            tuple: A tuple containing the book data from Google Books and the response status code.
        """
        google_books_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        try:
            response = requests.get(google_books_url)
            if response.json().get('totalItems', 0) == 0:
                return {"error": "no items returned from Google Books API for given ISBN number"}, 400
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
        Fetch book language data from Open Library API using the ISBN.

        Args:
            isbn (str): The ISBN of the book.

        Returns:
            tuple: A tuple containing the book data from Open Library and the response status code.
        """
        open_lib_books_url = f"https://openlibrary.org/search.json?q={isbn}&fields=language"
        try:
            response = requests.get(open_lib_books_url)
            if response.json().get('numFound', 0) == 0:
                return {"error": "no items returned from Open Library API for given ISBN number"}, 400
            else:
                open_lib_books_url = response.json()['docs'][0]
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}, 400

        book_google_api_data = {
            "language": open_lib_books_url.get("language"),
        }
        return book_google_api_data, 200

    @staticmethod
    def get_ai_api_key():
        """
        Retrieve the AI API key from a JSON file.

        Returns:
            str: The API key if loaded successfully, None otherwise.
        """
        try:
            with open('APIKeysData/APIKEY.json', 'r') as file:
                return json.load(file)["KEY"]
        except Exception as e:
            print(f"Failed to load AI API key: {e}")
            return None

    def get_book_ai_info(self, title: str, authors: str):
        """
        Generate a summary for the book using AI based on the title and authors.

        Args:
           title (str): The title of the book.
           authors (str): The authors of the book.

        Returns:
           str: A generated summary of the book.
        """
        if not self.api_key:
            return "AI service unavailable."

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(f"Summarize the book {title} by {authors} in 5 sentences or less.")
        return response.text
