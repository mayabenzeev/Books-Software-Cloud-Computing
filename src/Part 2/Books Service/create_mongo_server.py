from pymongo import MongoClient

class DBManager:
    def __init__(self):
        # Connect to the MongoDB server running on localhost at port 27017
        client = MongoClient('mongodb://localhost:27017/')
        self.db = client['AppDB']

    def get_collection(self, collection: str):
        return self.db[collection]
