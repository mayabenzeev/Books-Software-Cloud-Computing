import requests
import re
from bson import ObjectId


class BooksCollection:
    """
    A collection class for managing books and their ratings, leveraging external API data for enrichment.
    """

    BOOK_FIELDS = ["title", "authors", "ISBN", "publisher", "publishDate", "genre", "id", "_id"]

    def __init__(self, db):
        self.books_collection = db.books
        self.ratings_collection = db.ratings

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
        return isinstance(isbn, str) and len(isbn) == 13 and not self.books_collection.find_one({"ISBN": isbn})

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

        # book_id = str(uuid.uuid4())
        book_google_api_data, response_code = self.get_book_google_data(isbn)
        if response_code != 200:
            return book_google_api_data, response_code
        authors = publisher = published_date = "missing"

        if response_code == 200:
            # handles the case that there is more than one author
            authors = " and ".join(book_google_api_data["authors"])
            publisher = book_google_api_data["publisher"]
            # validate that published date is in the correct format, else define "missing"
            published_date_str = book_google_api_data["publishedDate"]
            published_date = published_date_str if BooksCollection.validate_publish_date(published_date_str) else (
                published_date)

        book = dict(title=title, authors=authors, ISBN=isbn, publisher=publisher, publishedDate=published_date,
                    genre=genre)
        book_insert_results = self.books_collection.insert_one(book)
        self.ratings_collection.insert_one({'_id': book_insert_results.inserted_id,
                                            'values': [], 'average': 0, 'title': title})
        return str(book_insert_results.inserted_id), 201

    def get_book(self, query: dict):
        """
        Retrieve books that match the specified query parameters.

        Args:
            query (dict): Query parameters for book search.

        Returns:
            tuple: A tuple of the filtered book list and response status code.
        """
        if not query:
            books_list = [BooksCollection.convert_id_to_string(book) for book in self.books_collection.find()]
            return books_list, 200  # Return all books if no query specified

        # Check if the key 'id' exists and rename it to '_id'
        if 'id' in query:
            query['_id'] = query.pop('id')
        # Cast the value of '_id' to ObjectId
        if '_id' in query:
            if len(query['_id']) != 24:
                return f"Id {query['_id']} is not a recognized id", 404
            query['_id'] = ObjectId(query['_id'])

        # Validate query fields
        for field in query:
            if field not in self.BOOK_FIELDS:
                return None, 422  # Return 422 status code if field is not recognized
            if field == "genre" and not self.validate_genre(query[field]):
                return None, 422  # Return 422 status code if genre is not valid

        # Execute the query
        filtered_books = [BooksCollection.convert_id_to_string(book) for book in self.books_collection.find(query)]
        if not filtered_books:
            return [], 200  # Return empty list if no books match the query
        return filtered_books, 200

    def get_book_by_id(self, book_id: str):
        """
        Retrieve a book by its unique ID.

        Args:
            book_id (str): The unique identifier of the book in the db.

        Returns:
            tuple: A tuple containing the book or None if not found, and the response status code.
        """
        result = self.books_collection.find_one({"_id": ObjectId(book_id)})
        # if the {id} is not a recognized id
        if not result:
            return None, 404
        return BooksCollection.convert_id_to_string(result), 200

    def update_book(self, put_values: dict):
        """
       Update the details of an existing book based on provided values.

       Args:
           put_values (dict): A dictionary containing all fields to update.

       Returns:
           tuple: A tuple containing the updated book ID if successful, None if not, and the response status code.
       """
        # genre is not one of excepted values
        if not BooksCollection.validate_genre(put_values["genre"]):
            return None, 422
        book_id = put_values.pop("id")
        id_query = {"_id": ObjectId(book_id)}
        update_query = {"$set": put_values}

        # find a book by its id and update by payload in /books resource
        try:
            update_res = self.books_collection.update_one(id_query, update_query)
            if update_res.matched_count == 0:  # id is not a recognized id
                return None, 404
            else:
                return book_id, 200
        except Exception as e:  # maybe an processable content
            return None, 422

    def delete_book(self, book_id: str):
        """
        Delete a book from the database by its ID.

        Args:
            book_id (str): The unique identifier of the book to delete in the db.

        Returns:
            tuple: A tuple containing the ID of the deleted book if successful,
            None if not, and the response status code.
        """
        query = {"_id": ObjectId(book_id)}
        # Attempt to delete the document
        result = self.books_collection.delete_one(query)
        # Check if a document was deleted
        if result.deleted_count > 0:
            self.ratings_collection.delete_one(query)
            return book_id, 200  # Successfully deleted
        else:
            return None, 404   # ID is not a recognized id

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

        query = {"_id": ObjectId(book_id)}
        document = self.ratings_collection.find_one(query)
        if document:
            ratings = document.get("values", [])
            ratings.append(rate)
            new_average = sum(ratings) / len(ratings)

            # Update the document with new ratings and average
            update_result = self.ratings_collection.update_one(
                query,
                {"$set": {"values": ratings, "average": new_average}}
            )
            if update_result.modified_count > 0:
                return book_id, new_average, 201  # Successfully updated
            else:
                return None, None, 404  # Update failed

        else:
            return None, None, 404  # ID is not a recognized id

    def get_book_ratings_by_id(self, book_id: str):
        """
        Retrieve the ratings for a specific book by its ID in the db.

        Args:
            book_id (str): The ID of the book in the db whose ratings are to be retrieved.

        Returns:
            tuple: A tuple containing the ratings if found, None if not, and the response status code.
        """
        result = self.ratings_collection.find_one({"_id": ObjectId(book_id)})
        # if the {id} is not a recognized id
        if not result:
            return None, 404
        return BooksCollection.convert_id_to_string(result), 200

    def get_book_ratings(self, query: dict):
        """
        Retrieve the ratings for all books.

        Returns:
            tuple: A tuple containing all ratings and the response status code.
        """
        # If not specified, return all ratings data
        if not query:
            ratings_list = [BooksCollection.convert_id_to_string(rating) for rating in self.ratings_collection.find()]
            return ratings_list, 200

        # Check for invalid query fields or unsupported genres
        for field, value in query.items():
            if field not in self.BOOK_FIELDS:
                return None, 422  # Bad request due to incorrect field names
            if field == "genre" and not self.validate_genre(value):
                return None, 422  # Bad request due to unsupported genre

        # Execute the query
        filtered_ratings = [BooksCollection.convert_id_to_string(rating) for rating in
                            self.ratings_collection.find(query)]
        if not filtered_ratings:
            return [], 200  # No results found, but the query was valid
        return filtered_ratings, 200

    def get_top(self):
        """
        Retrieve the top three books with the highest average ratings that have at least three ratings.

        Returns:
            tuple: A tuple containing the list of top-rated books and the response status code.
        """
        # Aggregation pipeline to find the top 3 books
        relevant_ratings_pipeline = [
            {"$match": {"$expr": {"$gte": [{"$size": "$values"}, 3]}}},
            # Corrected to filter documents with at least 3 ratings
            {"$sort": {"average": -1}},  # Sort documents by the average field in descending order
            {"$limit": 3}  # Limit the results to the top 3
        ]

        # Execute the aggregation pipeline
        top_books = [BooksCollection.convert_id_to_string(rate) for rate in self.ratings_collection.aggregate(relevant_ratings_pipeline)]
        return top_books, 200  # Return the top books and status code

    @staticmethod
    def convert_id_to_string(book: dict):
        """
        Convert the '_id' field of a book document to a string.

        Args:
            book (dict): A book document.

        Returns:
            dict: The book document with the '_id' field as a string.
        """
        if '_id' in book:
            book['_id'] = str(book['_id'])
        return book

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
