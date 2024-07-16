from flask_pymongo import PyMongo
from flask import Flask
from flask_restful import Api
from BooksCollection import *
from BooksAPI import Books, BooksId, Ratings, RatingsId, RatingsIdValues, Top  # Import resources

app = Flask(__name__)  # initialize Flask
api = Api(app)  # create API

app.config["MONGO_URI"] = "mongodb://mongodb:27017/AppDB"  # Use Docker service name for MongoDB
# app.config["MONGO_URI"] = "mongodb://localhost:27017/AppDB"  # Use Docker service name for MongoDB
mongo = PyMongo(app)
books_collection = BooksCollection(mongo.db)


if __name__ == "__main__":
    api.add_resource(Books, '/books', resource_class_args=[books_collection])
    api.add_resource(BooksId, '/books/<string:book_id>', resource_class_args=[books_collection])
    api.add_resource(RatingsIdValues, '/ratings/<string:book_id>/values', resource_class_args=[books_collection])
    api.add_resource(Top, '/top', resource_class_args=[books_collection])
    api.add_resource(RatingsId, '/ratings/<string:book_id>', resource_class_args=[books_collection])
    api.add_resource(Ratings, '/ratings', resource_class_args=[books_collection])

    app.run(host='0.0.0.0', port=80, debug=True)
