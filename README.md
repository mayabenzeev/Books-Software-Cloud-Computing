# Creating RESTful API for books
## Table of contents
* [General info](#general-info)
* [Project Overview](#Project-Overview)
* [Resources and Operations](#Resources-and-Operations)
* [Setup](#Setup)

## General info
This is a Project 1/3 of Cloud Computing and Software Engineering Course

## Project Overview:
* Invoking RESTful APIs
* Providing a RESTful API
* Use Docker containers for the application packaging and submitting.
* Deploying an application with four services using Docker Compose, including a MongoDB database, and an NGINX reverse-proxy.
* Ensuring data persistency and Auto-Restart services upon failure.
* Traffic Management and Load Balancing using NGINX across multiple instances of a service.

## Resources and Operations:
/books : POST, GET<br />
/books/{id} : PUT, DELETE, GET<br />
/ratings : GET<br />
/ratings/{id} : GET<br />
/ratings/{id}/values : POST<br />
/top : GET

Added in part 2:<br />
/loans : POST, GET<br />
/loans/{id} : GET, DELETE<br />

NGINX configurations for part 2:
* Librarian: Has full access to the books microservice via port 5001, capable of performing POST, DELETE, PUT, and GET requests on /books and /ratings.
* Member: Can interact with the loans service through port 5002, authorized to POST, DELETE, and GET information on /loans. This role also requires access to GET data from the /books resource for specific loan operations.
* Public: Limited to GET operations on /books, /ratings, /top, and /loans. Additionally, the public can POST to /ratings/{id}/values.

## Setup
To run and build the part 1 docker container, run the following commands:
```
$ cd src/Part\ 1
$ docker build --tag books:v1 .
$ docker run -p 8000:8000 books:v1
```
The container will listen on http://127.0.0.1:8000

To run and build the part 2 docker compose with NGINX reverse-proxy, run the following commands:
```
$ cd src/Part\ 2
$ docker compose up --build
```
Requests as allowed by the Part 2 configurations mentioned earlier.

#### Collaborators: Maya Ben-Zeev ; Noga Brenner ; Eden Zehavi


