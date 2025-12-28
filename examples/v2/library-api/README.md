# Library Management API

A complete REST API example demonstrating a library management system built with FDSL.

## Database Schema

The library system consists of five main entities:

### Core Entities
- **Authors** - Book authors with biographical information
- **Categories** - Book categories/genres
- **Books** - Library books with ISBN, copies, etc.
- **Members** - Library patrons/members
- **Loans** - Borrowing records

### Relationships
```
Author (1) ──< (N) Book
Category (1) ──< (N) Book
Member (1) ──< (N) Loan
Book (1) ──< (N) Loan
```

## Features

### Full CRUD Operations
All base entities support complete CRUD operations:
- **List** - Get all records with optional filtering
- **Read** - Get single record by ID
- **Create** - Add new record
- **Update** - Modify existing record
- **Delete** - Remove record

### Derived Entities
- **BookDetails** - Books enriched with author and category names
- **LoanDetails** - Loans with book and member information
- **MemberStats** - Member statistics (total loans, fines, etc.)
- **LibraryStatistics** - Overall library statistics (singleton)

### Read-only Fields
Certain fields are automatically managed:
- `id` - Auto-generated on creation
- `createdAt` - Timestamp of creation
- `joinedDate` - Member join date
- `loanDate` - Loan start date
- `fine` - Calculated fine amount

## Running the Example

### 1. Start the Dummy Library Service

```bash
cd examples/v2/library-api/dummy-service
docker compose -p thesis up --build
```

Service will be available at `http://localhost:9200`

### 2. Generate the FDSL API

```bash
fdsl generate examples/v2/library-api/main.fdsl --out examples/v2/library-api/generated
```

### 3. Run the Generated API

```bash
cd examples/v2/library-api/generated
docker compose -p thesis up --build
```

API will be available at `http://localhost:8000`

### 4. Access the UI

Open your browser to `http://localhost:3000` to see:
- Books table with author and category information
- Loans table with borrower and book details
- Members table
- Member statistics table

## API Endpoints

### Base Entities (Full CRUD)
- `GET /api/authors` - List all authors
- `GET /api/authors/{id}` - Get author by ID
- `POST /api/authors` - Create author
- `PUT /api/authors/{id}` - Update author
- `DELETE /api/authors/{id}` - Delete author

(Similar endpoints for: books, categories, members, loans)

### Derived Entities (Read-only)
- `GET /api/bookdetails` - List books with enriched data
- `GET /api/bookdetails/{id}` - Get book details
- `GET /api/loandetails` - List loans with full information
- `GET /api/memberstats` - Member statistics
- `GET /api/librarystatistics` - Overall statistics (singleton)

## Sample Data

The dummy service includes:
- 3 Authors (Orwell, Austen, García Márquez)
- 3 Categories (Fiction, Classic Literature, Science Fiction)
- 4 Books (1984, Pride and Prejudice, One Hundred Years of Solitude, Animal Farm)
- 3 Members (Alice, Bob, Carol)
- 4 Loans (active, overdue, and returned loans)

## Example Queries

### Get all available books
```
GET /api/bookdetails
Filter: availableCopies > 0
```

### Get overdue loans
```
GET /api/loandetails
Filter: status = "overdue"
```

### Get member with highest fines
```
GET /api/memberstats
Sort by: totalFines DESC
```

## Notes

- This example demonstrates the complete FDSL REST pattern
- All relationships are properly configured using the `relationships:` block
- Computed fields use FDSL expression language (map, filter, len, sum, etc.)
- Read-only fields are automatically excluded from create/update schemas
