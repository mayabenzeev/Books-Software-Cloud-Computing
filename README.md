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

## Resources and Operations:
/books : POST, GET<br />
/books/{id} : PUT, DELETE, GET<br />
/ratings : GET<br />
/ratings/{id} : GET<br />
/ratings/{id}/values : POST<br />
/top : GET

## Setup
To run and build the docker container run the following commands:
```
$ docker build --tag books:v1 .
$ docker run -p 8000:8000 books:v1
```
The container will listen on http://127.0.0.1:8000

#### Collaborators: Maya Ben-Zeev ; Noga Brenner ; Eden Zehavi


