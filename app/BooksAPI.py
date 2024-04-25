import json

from flask import request
from flask_restful import Resource, Api, reqparse
from BooksCollection import *
app = Flask(__name__) # initialize Flask
api = Api(app) # create API

books_collection = BooksCollection()

class Books(Resource):

    def post(self):
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
        except:
            return 'Incorrect POST format', 422  # at least one of the fields is missing
        id, status = books_collection.insert_book(title, isbn, genre)
        if status == 201:
            return f"Book Id {id} successfully created", 201
        return 'Incorrect POST format or book already exists', 422  # problem with data validation

    def get(self):
        query = request.args
        content, status = books_collection.get_book(dict(query))
        return json.dumps(content), status


class Ratings(Resource):
    def get(self):
        content, status = books_collection.get_book_ratings()
        return json.dumps(content), status


class RatingsIdValues(Resource):
    def post(self, id):
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return 'POST expects content_type to be application/json', 415  # unsupported media type

        parser = reqparse.RequestParser()
        parser.add_argument('value', type=float, required=True, location='json')
        args = parser.parse_args()
        try:
            value = args['value']
        except:
            return 'Incorrect POST format', 422  # at least one of the fields is missing
        _, avg, status = books_collection.rate_book(id, value)
        if status == 201:
            return f"The book {id} rating average was updated to {avg}", 201
        elif status == 404:
            return f"Id {id} is not a recognized id", 404
        else:
            return 'Incorrect POST format', 422  # problem with data validation


class Top(Resource):
    def get(self):
        content, status = books_collection.get_top()
        return json.dumps(content), status


class RatingsId(Resource):
    def get(self, id):
        content, status = books_collection.get_book_ratings_by_id(id)
        if status == 404:
            return f"Id {id} is not a recognized id", 404
        return json.dumps(content), status


class BooksId(Resource):
    def put(self, id):
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return 'POST expects content_type to be application/json', 415  # unsupported media type

        parser = reqparse.RequestParser()
        parser.add_argument('title', type=str, required=True, location='json')
        parser.add_argument('authors', type=str, required=True, location='json')
        parser.add_argument('ISBN', type=str, required=True, location='json')
        parser.add_argument('publisher', type=str, required=True, location='json')
        parser.add_argument('publishedDate', type=str, required=True, location='json')
        parser.add_argument('genre', type=str, required=True, location='json')
        parser.add_argument('language', type=list, required=True, location='json')
        parser.add_argument('summary', type=str, required=True, location='json')
        args = parser.parse_args()

        try:
            title = args["title"]
            authors = args["authors"]
            isbn = args["ISBN"]
            publisher = args["publisher"]
            published_date = args["publishedDate"]
            genre = args["genre"]
            language = args["language"]
            summary = args["summary"]
        except:
            return 'Incorrect POST format', 422  # at least one of the fields is missing
        put_values = {"title": title,
                      "authors": authors,
                      "ISBN": isbn,
                      "publisher": publisher,
                      "publishedData": published_date,
                      "genre": genre,
                      "language": language,
                      "summary": summary,
                      "id": id}
        id, status = books_collection.update_book(put_values)
        if status == 200:
            return f"The book {id} values updated successfully", 200
        elif status == 404:
            return f"Id {id} is not a recognized id", 404
        else:
            return 'Incorrect POST format', 422  # problem with data validation

    def get(self, id):
        content, status = books_collection.get_book_by_id(id)
        if status == 404:
            return f"Id {id} is not a recognized id", 404
        return json.dumps(content), status

    def delete(self, id):
        _, status = books_collection.delete_book(id)
        if status == 404:
            return f"Id {id} is not a recognized id", 404
        else:
            return f"Id {id} deleted successfully", status


api.add_resource(Books, '/books')
api.add_resource(BooksId, '/books/<string:id>')
api.add_resource(RatingsIdValues, '/ratings/<string:id>/values')
api.add_resource(Top, '/top')
api.add_resource(RatingsId, '/ratings/<string:id>')
api.add_resource(Ratings, '/ratings')


if __name__ == "__main__":
    print("running books-API")
    # run Flask app
    app.run(host='0.0.0.0', port=8000, debug=True)
