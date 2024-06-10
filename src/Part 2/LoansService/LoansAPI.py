from flask import request
from flask_restful import Resource, reqparse


class Loans(Resource):
    """
    Resource for handling loans creation and retrieval.
    """

    def __init__(self, loans_collection):
        self.loans_collection = loans_collection

    def post(self):
        """
        Handles POST request to create a new loan. Validates and inserts loan data.

        Returns:
            Tuple of message and response status code.
        """
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return 'POST expects content_type to be application/json', 415  # unsupported media type

        parser = reqparse.RequestParser()
        parser.add_argument('memberName', type=str, required=True, location='json')
        parser.add_argument('ISBN', type=str, required=True, location='json')
        parser.add_argument('loanDate', type=str, required=True, location='json')
        args = parser.parse_args()
        try:
            member_name = args['memberName']
            isbn = args['ISBN']
            loan_date = args['loanDate']
        except KeyError:
            return 'Incorrect POST format', 422  # at least one of the fields is missing

        loan_returned_message, status = self.loans_collection.insert_loan(member_name, isbn, loan_date)
        if status == 201:
            return f"Loans Id {str(loan_returned_message)} successfully created", 201
        return loan_returned_message, 422  # problem with data validation

    def get(self):
        """
        Handles GET request to retrieve loan based on query parameters.

        Returns:
            JSON list of loans and response status code.
        """
        query = request.args
        content, status = self.loans_collection.get_loans(dict(query))
        if status == 422:
            return "Bad query format", status
        return content, status

class LoansId(Resource):
    """
    Resource for handling retrieval, and deletion of a specific loan by its ID.
    """
    def __init__(self, loans_collection):
        self.loans_collection = loans_collection

    def get(self, loan_id: str):
        """
        Retrieves a specific loan by its ID.

        Args:
            loan_id (str): The ID of the loan in the db.

        Returns:
            JSON representation of the book or error message and response status code.
        """
        content, status = self.loans_collection.get_loan_by_id(loan_id)
        if status == 404:
            return f"Id {loan_id} is not a recognized id", 404

        return content, status

    def delete(self, loan_id: str):
        """
        Deletes a specific loan by its ID.

        Args:
            loan_id (str): The ID of the loan to delete in the db.

        Returns:
            Message indicating the result and response status code.
        """
        _, status = self.loans_collection.delete_book(loan_id)
        if status == 404:
            return f"Id {loan_id} is not a recognized id", 404
        else:
            return f"Id {loan_id} deleted successfully", status
#

