"""
Dummy Library Service - Provides REST endpoints for library management
Runs on port 9200
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uvicorn

app = FastAPI(title="Dummy Library Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample data
authors_db = [
    {"id": "a1", "name": "George Orwell", "birthYear": 1903, "nationality": "British", "biography": "English novelist and essayist", "createdAt": "2024-01-01T00:00:00Z"},
    {"id": "a2", "name": "Jane Austen", "birthYear": 1775, "nationality": "British", "biography": "English novelist", "createdAt": "2024-01-02T00:00:00Z"},
    {"id": "a3", "name": "Gabriel García Márquez", "birthYear": 1927, "nationality": "Colombian", "biography": "Colombian novelist and Nobel laureate", "createdAt": "2024-01-03T00:00:00Z"},
]

categories_db = [
    {"id": "c1", "name": "Fiction", "description": "Literary fiction and novels"},
    {"id": "c2", "name": "Classic Literature", "description": "Timeless literary works"},
    {"id": "c3", "name": "Science Fiction", "description": "Speculative and futuristic fiction"},
]

books_db = [
    {"id": "b1", "isbn": "978-0-452-28423-4", "title": "1984", "authorId": "a1", "categoryId": "c3", "publishedYear": 1949, "pages": 328, "language": "English", "availableCopies": 3, "totalCopies": 5, "createdAt": "2024-01-10T00:00:00Z"},
    {"id": "b2", "isbn": "978-0-14-143951-8", "title": "Pride and Prejudice", "authorId": "a2", "categoryId": "c2", "publishedYear": 1813, "pages": 432, "language": "English", "availableCopies": 2, "totalCopies": 3, "createdAt": "2024-01-11T00:00:00Z"},
    {"id": "b3", "isbn": "978-0-06-088328-7", "title": "One Hundred Years of Solitude", "authorId": "a3", "categoryId": "c1", "publishedYear": 1967, "pages": 417, "language": "Spanish", "availableCopies": 1, "totalCopies": 2, "createdAt": "2024-01-12T00:00:00Z"},
    {"id": "b4", "isbn": "978-0-452-28424-1", "title": "Animal Farm", "authorId": "a1", "categoryId": "c1", "publishedYear": 1945, "pages": 112, "language": "English", "availableCopies": 0, "totalCopies": 2, "createdAt": "2024-01-13T00:00:00Z"},
]

members_db = [
    {"id": "m1", "name": "Alice Johnson", "email": "alice@example.com", "phone": "555-0101", "address": "123 Main St", "membershipType": "premium", "joinedDate": "2023-06-15", "active": True},
    {"id": "m2", "name": "Bob Smith", "email": "bob@example.com", "phone": "555-0102", "address": "456 Oak Ave", "membershipType": "standard", "joinedDate": "2023-08-20", "active": True},
    {"id": "m3", "name": "Carol White", "email": "carol@example.com", "phone": "555-0103", "address": "789 Pine Rd", "membershipType": "standard", "joinedDate": "2024-01-10", "active": False},
]

loans_db = [
    {"id": "l1", "bookId": "b1", "memberId": "m1", "loanDate": "2024-12-01", "dueDate": "2024-12-15", "returnDate": None, "status": "active", "fine": 0.0},
    {"id": "l2", "bookId": "b2", "memberId": "m1", "loanDate": "2024-12-05", "dueDate": "2024-12-19", "returnDate": None, "status": "active", "fine": 0.0},
    {"id": "l3", "bookId": "b3", "memberId": "m2", "loanDate": "2024-11-15", "dueDate": "2024-11-29", "returnDate": None, "status": "overdue", "fine": 15.50},
    {"id": "l4", "bookId": "b4", "memberId": "m2", "loanDate": "2024-11-20", "dueDate": "2024-12-04", "returnDate": "2024-12-02", "status": "returned", "fine": 0.0},
]

# Authors endpoints
@app.get("/authors")
def list_authors():
    return authors_db

@app.get("/authors/{author_id}")
def get_author(author_id: str):
    for author in authors_db:
        if author["id"] == author_id:
            return author
    raise HTTPException(status_code=404, detail="Author not found")

@app.post("/authors")
def create_author(author: dict):
    author["id"] = f"a{len(authors_db) + 1}"
    author["createdAt"] = datetime.now().isoformat() + "Z"
    authors_db.append(author)
    return author

@app.put("/authors/{author_id}")
def update_author(author_id: str, author: dict):
    for i, a in enumerate(authors_db):
        if a["id"] == author_id:
            author["id"] = author_id
            author["createdAt"] = a["createdAt"]
            authors_db[i] = author
            return author
    raise HTTPException(status_code=404, detail="Author not found")

@app.delete("/authors/{author_id}")
def delete_author(author_id: str):
    for i, a in enumerate(authors_db):
        if a["id"] == author_id:
            authors_db.pop(i)
            return {"message": "Author deleted"}
    raise HTTPException(status_code=404, detail="Author not found")

# Categories endpoints
@app.get("/categories")
def list_categories():
    return categories_db

@app.get("/categories/{category_id}")
def get_category(category_id: str):
    for cat in categories_db:
        if cat["id"] == category_id:
            return cat
    raise HTTPException(status_code=404, detail="Category not found")

@app.post("/categories")
def create_category(category: dict):
    category["id"] = f"c{len(categories_db) + 1}"
    categories_db.append(category)
    return category

@app.put("/categories/{category_id}")
def update_category(category_id: str, category: dict):
    for i, c in enumerate(categories_db):
        if c["id"] == category_id:
            category["id"] = category_id
            categories_db[i] = category
            return category
    raise HTTPException(status_code=404, detail="Category not found")

@app.delete("/categories/{category_id}")
def delete_category(category_id: str):
    for i, c in enumerate(categories_db):
        if c["id"] == category_id:
            categories_db.pop(i)
            return {"message": "Category deleted"}
    raise HTTPException(status_code=404, detail="Category not found")

# Books endpoints
@app.get("/books")
def list_books():
    return books_db

@app.get("/books/{book_id}")
def get_book(book_id: str):
    for book in books_db:
        if book["id"] == book_id:
            return book
    raise HTTPException(status_code=404, detail="Book not found")

@app.post("/books")
def create_book(book: dict):
    book["id"] = f"b{len(books_db) + 1}"
    book["createdAt"] = datetime.now().isoformat() + "Z"
    books_db.append(book)
    return book

@app.put("/books/{book_id}")
def update_book(book_id: str, book: dict):
    for i, b in enumerate(books_db):
        if b["id"] == book_id:
            book["id"] = book_id
            book["createdAt"] = b["createdAt"]
            books_db[i] = book
            return book
    raise HTTPException(status_code=404, detail="Book not found")

@app.delete("/books/{book_id}")
def delete_book(book_id: str):
    for i, b in enumerate(books_db):
        if b["id"] == book_id:
            books_db.pop(i)
            return {"message": "Book deleted"}
    raise HTTPException(status_code=404, detail="Book not found")

# Members endpoints
@app.get("/members")
def list_members():
    return members_db

@app.get("/members/{member_id}")
def get_member(member_id: str):
    for member in members_db:
        if member["id"] == member_id:
            return member
    raise HTTPException(status_code=404, detail="Member not found")

@app.post("/members")
def create_member(member: dict):
    member["id"] = f"m{len(members_db) + 1}"
    member["joinedDate"] = datetime.now().date().isoformat()
    members_db.append(member)
    return member

@app.put("/members/{member_id}")
def update_member(member_id: str, member: dict):
    for i, m in enumerate(members_db):
        if m["id"] == member_id:
            member["id"] = member_id
            member["joinedDate"] = m["joinedDate"]
            members_db[i] = member
            return member
    raise HTTPException(status_code=404, detail="Member not found")

@app.delete("/members/{member_id}")
def delete_member(member_id: str):
    for i, m in enumerate(members_db):
        if m["id"] == member_id:
            members_db.pop(i)
            return {"message": "Member deleted"}
    raise HTTPException(status_code=404, detail="Member not found")

# Loans endpoints
@app.get("/loans")
def list_loans(memberId: str = None):
    if memberId:
        return [loan for loan in loans_db if loan["memberId"] == memberId]
    return loans_db

@app.get("/loans/{loan_id}")
def get_loan(loan_id: str):
    for loan in loans_db:
        if loan["id"] == loan_id:
            return loan
    raise HTTPException(status_code=404, detail="Loan not found")

@app.post("/loans")
def create_loan(loan: dict):
    loan["id"] = f"l{len(loans_db) + 1}"
    loan["loanDate"] = datetime.now().date().isoformat()
    loan["fine"] = 0.0
    loans_db.append(loan)
    return loan

@app.put("/loans/{loan_id}")
def update_loan(loan_id: str, loan: dict):
    for i, l in enumerate(loans_db):
        if l["id"] == loan_id:
            loan["id"] = loan_id
            loan["loanDate"] = l["loanDate"]
            loan["fine"] = l["fine"]
            loans_db[i] = loan
            return loan
    raise HTTPException(status_code=404, detail="Loan not found")

@app.delete("/loans/{loan_id}")
def delete_loan(loan_id: str):
    for i, l in enumerate(loans_db):
        if l["id"] == loan_id:
            loans_db.pop(i)
            return {"message": "Loan deleted"}
    raise HTTPException(status_code=404, detail="Loan not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9200)
