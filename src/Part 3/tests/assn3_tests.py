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


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    print("cleanup")
    url = "http://localhost:5001/books"
    # First, get all the books
    get_response = requests.get(BASE_URL)
    if get_response.status_code == 200:
        books = get_response.json()  # Assuming the response returns a JSON list of books
        # Loop through each book and delete it
        for book in books:
            delete_response = requests.delete(f"{url}/{book['_id']}")
            if delete_response.status_code != 200:
                print(f"Failed to delete book ID {book['_id']}: {delete_response.status_code}, {delete_response.text}")
    else:
        print(f"Failed to retrieve books for cleanup: {get_response.status_code}, {get_response.text}")

@pytest.fixture(scope="module")
def create_books():
    ids = []
    for book in books[:3]:  # first three books
        response = requests.post(BASE_URL, json=book)
        assert response.status_code == 201, f"POST failed for book: {book['title']}, received status: {response.status_code}"
        response_data = response.json()
        print(response_data)
        assert 'ID' in response_data, "No ID returned in response"
        ids.append(response_data['ID'])
    return ids


def test_post_unique_ids(create_books):
    # Check if all IDs are unique
    assert len(set(create_books)) == len(create_books), "IDs are not unique"


def test_get_individual_book(create_books):
    book_id = create_books[0]  # Assuming ID of "Adventures of Huckleberry Finn"
    response_data = requests.get(f"{BASE_URL}/{book_id}")

    # Extract the ID from the POST response
    assert '_id' in response_data.json(), "No ID returned in response"

    # GET the book by ID
    assert response_data.status_code == 200, "Failed to retrieve book by ID"

    # Check response
    book_data = response_data.json()
    assert book_data['authors'] == "Mark Twain", "Authors field does not match"


def test_get_books(create_books):
    # Check status code from the GET request is 200
    response = requests.get(BASE_URL)
    assert response.status_code == 200, "Failed to fetch all books"

    # Check JSON returned object contains 3 embedded JSON objects
    books_data = response.json()
    assert len(books_data) == len(create_books), "The number of books retrieved does not match expected"
    for book in books_data:
        assert isinstance(book, dict), "Book data is not in JSON object format"


def test_post_invalid_isbn():
    # Book with invalid ISBN
    invalid_book = books[3]
    response = requests.post(BASE_URL, json=invalid_book)
    assert response.status_code in [400, 500], f"Expected status code 400 or 500, got {response.status_code}"

def test_delete_book(create_books):
    book_id = create_books[1]  # The Best of Isaac Asimov

    # delete the book by ID
    delete_response = requests.delete(f"{BASE_URL}/{book_id}")
    assert delete_response.status_code == 200, "Failed to delete the book by ID"

    # Optionally, verify that the book no longer exists
    get_response = requests.get(f"{BASE_URL}/{book_id}")
    assert get_response.status_code == 404, "Book still exists after deletion"

def test_get_deleted_book(create_books):
    deleted_book_id = create_books[1]  # The Best of Isaac Asimov
    response = requests.get(f"{BASE_URL}/{deleted_book_id}")
    assert response.status_code == 404, "Expected status code 404 for non-existent book"


def test_post_book_invalid_genre():
    invalid_genre_book = books[4]
    response = requests.post(BASE_URL, json=invalid_genre_book)
    assert response.status_code == 422, f"Expected status code 422 for invalid genre, got {response.status_code}"


