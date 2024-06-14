from flask_pymongo import PyMongo
from flask import Flask
from flask_restful import Api
from LoansCollection import *
from LoansAPI import Loans, LoansId  # Import resources

app = Flask(__name__)  # initialize Flask
api = Api(app)  # create API

app.config["MONGO_URI"] = "mongodb://mongodb:27017/AppDB"  # Use Docker service name for MongoDB
mongo = PyMongo(app)
loans_collection = LoansCollection(mongo.db)


if __name__ == "__main__":
    api.add_resource(Loans, '/loans', resource_class_args=[loans_collection])
    api.add_resource(LoansId, '/loans/<string:loan_id>', resource_class_args=[loans_collection])

    app.run(host='0.0.0.0', port=80, debug=True)
