from flask import Flask
from flask_restful import Api
from BooksService.BooksCollection import *
from LoansService.LoansCollection import *
from CreateMongoServer import DBManager
from BooksService.BooksAPI import Books, BooksId, Ratings, RatingsId, RatingsIdValues, Top  # Import resources
from LoansService.LoansAPI import Loans, LoansId  # Import resources


app = Flask(__name__)  # initialize Flask
api = Api(app)  # create API
db = DBManager()
books_collection = BooksCollection(db)
loans_collection = LoansCollection(db)


if __name__ == "__main__":
    api.add_resource(Books, '/books', resource_class_args=[books_collection])
    api.add_resource(BooksId, '/books/<string:book_id>', resource_class_args=[books_collection])
    api.add_resource(RatingsIdValues, '/ratings/<string:book_id>/values', resource_class_args=[books_collection])
    api.add_resource(Top, '/top', resource_class_args=[books_collection])
    api.add_resource(RatingsId, '/ratings/<string:book_id>', resource_class_args=[books_collection])
    api.add_resource(Ratings, '/ratings', resource_class_args=[books_collection])
    api.add_resource(Loans, '/loans', resource_class_args=[loans_collection])
    api.add_resource(LoansId, '/loans/<string:loan_id>', resource_class_args=[loans_collection])

    app.run(host='0.0.0.0', port=8000, debug=True)