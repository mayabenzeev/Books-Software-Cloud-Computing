import requests
import pytest

BASE_URL = "http://localhost:5001/books"

books = [
    {"title": "Adventures of Huckleberry Finn", "ISBN": "9780520343641", "genre": "Fiction"},
    {"title": "The Best of Isaac Asimov", "ISBN": "9780385050784", "genre": "Science Fiction"},
    {"title": "Fear No Evil", "ISBN": "9780394558783", "genre": "Biography"},
    {"title": "No such book", "ISBN": "0000001111111", "genre": "Biography"},  # Invalid ISBN
    {"title": "The Greatest Joke Book Ever", "authors": "Mel Greene", "ISBN": "9780380798490", "genre": "Jokes"},  # Invalid Genre
    {"title": "The Adventures of Tom Sawyer", "ISBN": "9780195810400", "genre": "Fiction"},
    {"title": "I, Robot", "ISBN": "9780553294385", "genre": "Science Fiction"},
    {"title": "Second Foundation", "ISBN": "9780553293364", "genre": "Science Fiction"}
]


@pytest.fixture(scope="module")
def create_books(books):
    ids = []
    for book in books[:3]:  # first three books
        response = requests.post(BASE_URL, json=book)
        assert response.status_code == 201, f"POST failed for book: {book['title']}, received status: {response.status_code}"
        response_data = response.json()
        assert 'ID' in response_data, "No ID returned in response"
        ids.append(response_data['ID'])
    return ids
def test_post_unique_ids(create_3_books):
    # Check if all IDs are unique
    assert len(set(create_3_books)) == len(create_3_books), "IDs are not unique"

def test_get_individual_book1(create_3_books):
    book_id = create_3_books[0]  # Assuming ID of "Adventures of Huckleberry Finn"
    response_data = requests.get(f"{BASE_URL}/{book_id}")

    # Extract the ID from the POST response
    assert 'ID' in response_data, "No ID returned in response"
    book_id = response_data['ID']

    # GET the book by ID
    get_response = requests.get(f"{BASE_URL}/{book_id}")
    assert get_response.status_code == 200, "Failed to retrieve book by ID"

    # Check response
    book_data = get_response.json()
    assert book_data['authors'] == "Mark Twain", "Authors field does not match"

def test_get_books(create_3_books):
    # Check status code from the GET request is 200
    response = requests.get(BASE_URL)
    assert response.status_code == 200, "Failed to fetch all books"

    # Check JSON returned object contains 3 embedded JSON objects
    books_data = response.json()
    assert len(books_data) == len(create_3_books), "The number of books retrieved does not match expected"
    for book in books_data:
        assert isinstance(book, dict), "Book data is not in JSON object format"


def test_post_invalid_isbn():
    # Book with invalid ISBN
    invalid_book = books[3]  #TODO: CHECK GOOGLE API RESPONSE
    response = requests.post(BASE_URL, json=invalid_book)
    assert response.status_code in [400, 500], f"Expected status code 400 or 500, got {response.status_code}"

# def create_book(book_json):
#     response = requests.post(BASE_URL, json=book_json)
#     assert response.status_code == 201, f"POST failed for book: {book_json['title']}, received status: {response.status_code}"
#     response_json = response.json()
#     return response_json
