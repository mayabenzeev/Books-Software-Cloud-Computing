from flask import Flask
from flask_restful import Api
from BooksService.BooksCollection import *
from CreateMongoServer import DBManager

app = Flask(__name__)  # initialize Flask
api = Api(app)  # create API
db = DBManager()
books_collection = BooksCollection(db)


if __name__ == "__main__":
    print("running books-API")

    # run Flask app
    app.run(host='0.0.0.0', port=8000, debug=True)
