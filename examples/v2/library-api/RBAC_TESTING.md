Public Access (No Authentication Required)

# List all authors (public can read)
curl http://localhost:8000/api/authors

# Get a specific author
curl http://localhost:8000/api/authors/1

# List all books (public can read)
curl http://localhost:8000/api/books

# Get a specific book
curl http://localhost:8000/api/books/1

# Get book details (composite entity, public can read)
curl http://localhost:8000/api/books/1/bookdetails

# List all categories (public can read)
curl http://localhost:8000/api/categories

# Get a specific category
curl http://localhost:8000/api/categories/1
Librarian Access (Requires Authentication)
First, generate a librarian token:

python generate_token.py --user librarian_user --roles librarian
Then use the token in requests:

# Export token for convenience
export TOKEN="<paste-token-here>"

# Create a new author (librarian can create)
curl -X POST http://localhost:8000/api/authors \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Austen",
    "birthYear": 1775,
    "nationality": "British",
    "biography": "English novelist known for her six major novels"
  }'

# Update an author (librarian can update)
curl -X PUT http://localhost:8000/api/authors/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Austen (Updated)",
    "birthYear": 1775,
    "nationality": "British",
    "biography": "English novelist known for her wit and social commentary"
  }'

# Create a new book
curl -X POST http://localhost:8000/api/books \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "isbn": "978-0141439518",
    "title": "Pride and Prejudice",
    "authorId": "1",
    "categoryId": "1",
    "publishedYear": 1813,
    "language": "English",
    "totalCopies": 5,
    "availableCopies": 3
  }'

# Create a new member
curl -X POST http://localhost:8000/api/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "membershipType": "premium",
    "joinDate": "2024-01-01",
    "active": "true"
  }'

# Create a loan
curl -X POST http://localhost:8000/api/loans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bookId": "1",
    "memberId": "1",
    "loanDate": "2024-01-15",
    "dueDate": "2024-02-15",
    "status": "active",
    "fine": 0.0
  }'

# Read-only composite entities (librarian can read)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/loans/1/loandetails
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/members/1/memberstats
Admin Access (Full Access)
Generate an admin token:

python generate_token.py --user admin_user --roles admin

export ADMIN_TOKEN="<paste-admin-token-here>"

# Delete an author (only admin can delete)
curl -X DELETE http://localhost:8000/api/authors/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Delete a book
curl -X DELETE http://localhost:8000/api/books/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Delete a member
curl -X DELETE http://localhost:8000/api/members/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Delete a loan
curl -X DELETE http://localhost:8000/api/loans/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Admin can also access library statistics
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/books/1/librarystatistics
Test Authentication Failures

# Try to create without token (should fail with 403)
curl -X POST http://localhost:8000/api/authors \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Author"}'

# Try to delete with librarian token (should fail with 403)
curl -X DELETE http://localhost:8000/api/authors/1 \
  -H "Authorization: Bearer $TOKEN"
Multi-Role User
Generate a token with multiple roles:

python generate_token.py --user poweruser --roles "librarian,admin"
This user will have all permissions from both roles