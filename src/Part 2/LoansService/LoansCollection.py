import requests
import re
from bson import ObjectId

class LoansCollection:
    """
    A collection class for managing books and their ratings, leveraging external API data for enrichment.
    """

    LOAN_FIELDS = ["memberName", "ISBN", "title", "bookID", "loanDate", "loanID"]

    def __init__(self, db):
        self.loans_collection = db.get_collection("loans")
        self.books_collection = db.get_collection("books")

    @staticmethod
    def validate_member_name(name):
        """
        Validate that the name is a string and not empty.

        Args:
            name (str): The member name to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        return isinstance(name, str) and len(name) > 0


    @staticmethod
    def validate_loan_date(date):
        """
        Validate loan date against the pattern yyyy-mm-dd or yyyy.

        Args:
            date (str): The loan date string to validate.

        Returns:
            bool: True if the date matches the pattern, False otherwise.
        """
        pattern = r'^\d{4}-\d{2}-\d{2}$'  # pattern for the format yyyy-mm-dd
        return bool(re.match(pattern, date))  # Return if the string matches the pattern

    def validate_and_return_isbn(self, isbn):
        """
        Validate that the ISBN is exactly 13 characters long, exists within the database, and has not been loaned.

        Args:
            isbn (str): The ISBN to validate.

        Returns:
            dict: The book document from books db if the ISBN is valid, exists and not loaned, None otherwise.
        """
        if not isinstance(isbn, str) or len(isbn) != 13 or self.loans_collection.find_one({"ISBN": isbn}):
            return None
        return self.books_collection.find_one({"ISBN": isbn})

    def validate_data(self, name, loan_date, isbn):
        """
        Validate the name, loan date, and ISBN for a new loan.

        Args:
            name (str): The member name to validate.
            loan_date (str): The date to validate.
            isbn (str): The ISBN to validate that exists.

        Returns:
            dict: the book document if all validations pass, None otherwise.
        """
        book_document = self.validate_and_return_isbn(isbn)
        if LoansCollection.validate_member_name(name) and LoansCollection.validate_loan_date(
            loan_date) and book_document:
            return book_document
        else:
            return None

    def insert_loan(self, member_name: str, isbn: str, loan_date: str):
        """
        Insert a new loan into the database if it passes validation.

        Args:
            member_name (str): The member_name that wants to loan the book.
            isbn (str): The ISBN of the book.
            loan_date (str): The date of the loan.

        Returns:
            tuple: A tuple containing the loanID or false message, and response status code.
        """
        book_document = self.validate_data(member_name, isbn, loan_date)
        if not book_document:
            return "One of the inserted fields is not valid.", 422

        # Check existing loans
        if self.loans_collection.find({'memberName': member_name}).count() >= 2:
            return f"Member {member_name} has 2 loaned books and cannot loan another one.", 422

        # Prepare the loan document
        loan = {
            'memberName': member_name,
            'ISBN': isbn,
            'title': book_document.get("title"),
            'bookID': self.convert_id_to_string(book_document.get("_id")),
            'loanDate': loan_date
        }

        # Insert the loan into the database
        result = self.loans_collection.insert_one(loan)
        inserted_id = result.inserted_id

        # Update the document to set loanID as the _id value
        self.loans_collection.update_one({'_id': inserted_id}, {'$set': {'loanID': str(inserted_id)}})

        return inserted_id, 201

    def get_loans(self, query: dict):
        """
        Retrieve loans that match the specified query parameters.

        Args:
            query (dict): Query parameters for book search.

        Returns:
            tuple: A tuple of the filtered loans list and response status code.
        """
        if not query:
            loans_list = [LoansCollection.convert_id_to_string(loan) for loan in self.loans_collection.find()]
            return loans_list, 200  # Return all loans if no query specified

        # Check if the key 'loanID' exists and rename it to '_id'
        if 'loanID' in query:
            query['_id'] = query.pop('loanID')
        # Cast the value of '_id' to ObjectId
        if '_id' in query:
            query['_id'] = ObjectId(query['_id'])

        # Validate query fields
        for field in query:
            if field not in self.LOAN_FIELDS:
                return None, 422  # Return 422 status code if field is not recognized

        # Execute the query
        filtered_loans = [LoansCollection.convert_id_to_string(loan) for loan in self.loans_collection.find(query)]
        if not filtered_loans:
            return [], 200  # Return empty list if no loans match the query
        return filtered_loans, 200


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

        id_query = {"_id": ObjectId(put_values["id"])}
        update_query = {"$set": put_values}

        # find a book by its id and update by payload in /books resource
        try:
            update_res = self.books_collection.update_one(id_query, update_query)
            if update_res.matched_count == 0:  # id is not a recognized id
                return None, 404
            else:
                return update_res.upserted_id, 200
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
            ratings = document.get("ratings", [])
            ratings.append(rate)
            new_average = sum(ratings) / len(ratings)

            # Update the document with new ratings and average
            update_result = self.ratings_collection.update_one(
                query,
                {"$set": {"ratings": ratings, "average": new_average}}
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
        return result, 200

    def get_book_ratings(self, query: dict):
        """
        Retrieve the ratings for all books.

        Returns:
            tuple: A tuple containing all ratings and the response status code.
        """
        # If not specified, return all ratings data
        if not query:
            return list(self.ratings_collection.find()), 200

        # Check for invalid query fields or unsupported genres
        for field, value in query.items():
            if field not in self.BOOK_FIELDS:
                return None, 422  # Bad request due to incorrect field names
            if field == "genre" and not self.validate_genre(value):
                return None, 422  # Bad request due to unsupported genre

        # Execute the query
        filtered_ratings = list(self.ratings_collection.find(query))
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
            {"$match": {"values": {"$exists": True, "$size": {"$gte": 3}}}},  # Filter documents with at least 3 ratings
            {"$sort": {"average": -1}},  # Sort documents by the average field in descending order
            {"$limit": 3}  # Limit the results to the top 3
            ]

        # Execute the aggregation pipeline
        top_books = list(self.ratings_collection.aggregate(relevant_ratings_pipeline))
        return top_books, 200  # Return the top books and status code


    def search_by_field(self, field: str, value: str):
        """
        Helper function: Search for books in the db by a specific field and value.

        Args:
            field (str): The field to search by.
            value (str): The value to search for.

        Returns:
            list: A list of books that match the search criteria.
        """
        #TODO: check about the Authors field input (if can be list)
        # # Check if the value should be treated as an element in a list
        # if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
        #     # If value is intended to be a list, search for the value as an element in the list field
        #     query = {field: {"$in": [value.strip("[]")]}}
        # else:
        #     # Normal equality check
        if field == "id":
            field = "_id"
            value = ObjectId(value)

        get_query = {field: value}

        # Perform the query
        try:
            result = [BooksCollection.convert_id_to_string(book) for book in self.books_collection.find(get_query)]
            return result[0] if len(result) == 1 else result
        except KeyError:
            # If the field does not exist in any document
            return []
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

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
