import re
from bson import ObjectId


class LoansCollection:
    """
    A collection class for managing books and their ratings, leveraging external API data for enrichment.
    """

    LOAN_FIELDS = ["memberName", "ISBN", "title", "bookID", "loanDate", "loanID", "_id"]

    def __init__(self, db):
        self.loans_collection = db.loans
        self.books_collection = db.books

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

    def validate_data(self, name, isbn, loan_date):
        """
        Validate the name, loan date, and ISBN for a new loan.

        Args:
            name (str): The member name to validate.
            isbn (str): The ISBN to validate that exists.
            loan_date (str): The date to validate.

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
            'bookID': str(book_document.get("_id")),
            'loanDate': loan_date
        }

        # Insert the loan into the database
        result = self.loans_collection.insert_one(loan)
        inserted_id = result.inserted_id

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
            if len(query['_id'] != 24):
                #TODO: check return code
                return f"Id {query['_id']} is not a recognized id", 404
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

    def get_loan_by_id(self, loan_id: str):
        """
        Retrieve a loan by its unique ID.

        Args:
            loan_id (str): The unique identifier of the loan in the db.

        Returns:
            tuple: A tuple containing the loan or None if not found, and the response status code.
        """
        if len(loan_id) != 24:
            # TODO: check return code
            return f"Id {len(loan_id)} is not a recognized id", 404
        result = self.loans_collection.find_one({"_id": ObjectId(loan_id)})
        # if the {id} is not a recognized id
        if not result:
            return None, 404
        return LoansCollection.convert_id_to_string(result), 200

    def delete_book(self, loan_id: str):
        """
        Delete loan from the database by its ID.

        Args:
            loan_id (str): The unique identifier of the loan to delete in the db.

        Returns:
            tuple: A tuple containing the ID of the deleted loan if successful,
            None if not, and the response status code.
        """
        query = {"_id": ObjectId(loan_id)}
        # Attempt to delete the document
        result = self.loans_collection.delete_one(query)
        # Check if a document was deleted
        if result.deleted_count > 0:
            return loan_id, 200  # Successfully deleted
        else:
            return None, 404   # ID is not a recognized id


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
            book['loanID'] = book.pop('_id')
        if 'loanID' in book:
            book['loanID'] = str(book['loanID'])
        return book
