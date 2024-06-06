from flask import request, Flask
from flask_restful import Resource, Api, reqparse
from BooksCollection import *
from create_mongo_server import DBManager

app = Flask(__name__)  # initialize Flask
api = Api(app)  # create API

# books_collection = BooksCollection()
db = DBManager()

class Books(Resource):
    """
    Resource for handling book creation and retrieval.
    """

    def post(self):
        """
        Handles POST request to create a new book. Validates and inserts book data.

        Returns:
            Tuple of message and response status code.
        """
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return 'POST expects content_type to be application/json', 415  # unsupported media type

        parser = reqparse.RequestParser()
        parser.add_argument('title', type=str, required=True, location='json')
        parser.add_argument('ISBN', type=str, required=True, location='json')
        parser.add_argument('genre', type=str, required=True, location='json')
        args = parser.parse_args()
        try:
            title = args['title']
            isbn = args['ISBN']
            genre = args['genre']
        except KeyError:
            return 'Incorrect POST format', 422  # at least one of the fields is missing

        book_id, status = books_collection.insert_book(title, isbn, genre)
        if status == 201:
            return f"Book Id {str(book_id)} successfully created", 201
        return 'Incorrect POST format or book already exists', 422  # problem with data validation

    def get(self):
        """
        Handles GET request to retrieve books based on query parameters.

        Returns:
            JSON list of books and response status code.
        """
        query = request.args
        content, status = books_collection.get_book(dict(query))
        if status == 422:
            return "Bad query format", status
        return content, status


class Ratings(Resource):
    """
    Resource for handling retrieval of ratings for all books.
    """

    def get(self):
        """
        Retrieves ratings for all books.

        Returns:
            JSON list of ratings and response status code.
        """
        query = request.args
        content, status = books_collection.get_book_ratings(dict(query))
        if status == 422:
            return "Bad query format", status
        return content, status


class RatingsIdValues(Resource):
    """
    Resource for handling posting ratings to a specific book identified by its ID.
    """

    def post(self, book_id: str):
        """
        Posts a new rating for a book identified by its ID.

        Args:
            book_id (str): The ID of the book to rate in the db.

        Returns:
            Message indicating the result and response status code.
        """
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return 'POST expects content_type to be application/json', 415  # unsupported media type

        parser = reqparse.RequestParser()
        parser.add_argument('value', type=float, required=True, location='json')
        args = parser.parse_args()
        try:
            value = args['value']
        except KeyError:
            return 'Incorrect POST format', 422  # at least one of the fields is missing
        _, avg, status = books_collection.rate_book(book_id, value)
        if status == 201:
            return f"The book {book_id} rating average was updated to {avg}", 201
        elif status == 404:
            return f"Id {book_id} is not a recognized id", 404
        else:
            return 'Incorrect POST format', 422  # problem with data validation


class Top(Resource):
    """
    Resource for retrieving the top-rated books.
    """

    def get(self):
        """
        Retrieves the top-rated books in the db.

        Returns:
            JSON list of top-rated books and response status code.
        """
        content, status = books_collection.get_top()
        return content, status


class RatingsId(Resource):
    """
    Resource for retrieving ratings for a specific book by its ID.
    """

    def get(self, book_id: str):
        """
        Retrieves ratings for a specific book identified by its ID.

        Args:
            book_id (str): The ID of the book in the db.

        Returns:
            JSON representation of ratings or error message and response status code.
        """
        content, status = books_collection.get_book_ratings_by_id(book_id)
        if status == 404:
            return f"Id {book_id} is not a recognized id", 404
        return content, status


class BooksId(Resource):
    """
    Resource for handling updates, retrieval, and deletion of a specific book by its ID.
    """

    def put(self, book_id: str):
        """
        Updates a book's data identified by its ID.

        Args:
            book_id (str): The ID of the book to update in the db.

        Returns:
            Message indicating the result and response status code.
        """
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return 'PUT expects content_type to be application/json', 415  # unsupported media type

        parser = reqparse.RequestParser()
        parser.add_argument('title', type=str, required=True, location='json')
        parser.add_argument('authors', type=str, required=True, location='json')
        parser.add_argument('ISBN', type=str, required=True, location='json')
        parser.add_argument('publisher', type=str, required=True, location='json')
        parser.add_argument('publishedDate', type=str, required=True, location='json')
        parser.add_argument('genre', type=str, required=True, location='json')
        args = parser.parse_args()

        try:
            title = args["title"]
            authors = args["authors"]
            isbn = args["ISBN"]
            publisher = args["publisher"]
            published_date = args["publishedDate"]
            genre = args["genre"]
        except KeyError:
            return 'Incorrect PUT format', 422  # at least one of the fields is missing
        put_values = {"title": title,
                      "authors": authors,
                      "ISBN": isbn,
                      "publisher": publisher,
                      "publishedData": published_date,
                      "genre": genre,
                      "id": book_id}
        book_id, status = books_collection.update_book(put_values)
        if status == 200:
            return f"The book {str(book_id)} values updated successfully", 200
        elif status == 404:
            return f"Id {str(book_id)} is not a recognized id", 404
        else:
            return 'Incorrect PUT format', 422  # problem with data validation

    def get(self, book_id: str):
        """
        Retrieves a specific book by its ID.

        Args:
            book_id (str): The ID of the book in the db.

        Returns:
            JSON representation of the book or error message and response status code.
        """
        content, status = books_collection.get_book_by_id(book_id)
        if status == 404:
            return f"Id {book_id} is not a recognized id", 404

        return content, status

    def delete(self, book_id: str):
        """
        Deletes a specific book by its ID.

        Args:
            book_id (str): The ID of the book to delete in the db.

        Returns:
            Message indicating the result and response status code.
        """
        _, status = books_collection.delete_book(book_id)
        if status == 404:
            return f"Id {book_id} is not a recognized id", 404
        else:
            return f"Id {book_id} deleted successfully", status


api.add_resource(Books, '/books')
api.add_resource(BooksId, '/books/<string:book_id>')
api.add_resource(RatingsIdValues, '/ratings/<string:book_id>/values')
api.add_resource(Top, '/top')
api.add_resource(RatingsId, '/ratings/<string:book_id>')
api.add_resource(Ratings, '/ratings')

if __name__ == "__main__":
    print("running books-API")
    books_collection = BooksCollection()
    # run Flask app
    app.run(host='0.0.0.0', port=8000, debug=True)
