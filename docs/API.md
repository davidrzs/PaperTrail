# API Documentation

Base URL: `http://localhost:8000` (or your deployment URL)

## Authentication

PaperTrail uses JWT (JSON Web Token) authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### Authentication

#### Register User

```http
POST /auth/register
Content-Type: application/json

{
  "username": "john",
  "email": "john@example.com",
  "password": "secure-password",
  "display_name": "John Doe"
}
```

Response:
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "display_name": "John Doe",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Login

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=john&password=secure-password
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Get Current User

```http
GET /auth/me
Authorization: Bearer <token>
```

Response:
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "display_name": "John Doe"
}
```

### Papers

#### Create Paper

```http
POST /papers
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Attention Is All You Need",
  "authors": "Vaswani et al.",
  "arxiv_id": "1706.03762",
  "doi": "10.48550/arXiv.1706.03762",
  "paper_url": "https://arxiv.org/abs/1706.03762",
  "abstract": "The dominant sequence transduction models...",
  "summary": "Introduces the Transformer architecture using self-attention mechanisms instead of recurrence.",
  "tags": ["transformers", "attention", "nlp"],
  "date_read": "2024-01-15",
  "is_private": false
}
```

Note: `abstract` is optional. All other fields except `tags` are required.

Response:
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Attention Is All You Need",
  "authors": "Vaswani et al.",
  "arxiv_id": "1706.03762",
  "summary": "Introduces the Transformer architecture...",
  "tags": ["transformers", "attention", "nlp"],
  "is_private": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### List Papers

```http
GET /papers?limit=20&offset=0&user_id=1&tag=transformers
```

Query parameters:
- `limit` (optional): Number of results (default: 50, max: 100)
- `offset` (optional): Pagination offset (default: 0)
- `user_id` (optional): Filter by user
- `tag` (optional): Filter by tag name

Response:
```json
{
  "papers": [
    {
      "id": 1,
      "title": "Attention Is All You Need",
      "authors": "Vaswani et al.",
      "summary": "Introduces the Transformer...",
      "tags": ["transformers", "attention"],
      "date_read": "2024-01-15",
      "user": {
        "username": "john",
        "display_name": "John Doe"
      }
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### Get Single Paper

```http
GET /papers/1
```

Response:
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Attention Is All You Need",
  "authors": "Vaswani et al.",
  "arxiv_id": "1706.03762",
  "doi": "10.48550/arXiv.1706.03762",
  "paper_url": "https://arxiv.org/abs/1706.03762",
  "abstract": "The dominant sequence transduction...",
  "summary": "Introduces the Transformer architecture...",
  "tags": ["transformers", "attention", "nlp"],
  "is_private": false,
  "date_read": "2024-01-15",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "user": {
    "username": "john",
    "display_name": "John Doe"
  }
}
```

#### Update Paper

```http
PUT /papers/1
Authorization: Bearer <token>
Content-Type: application/json

{
  "summary": "Updated summary with more details...",
  "tags": ["transformers", "attention", "nlp", "deep-learning"]
}
```

Note: Only the paper owner can update. Partial updates supported.

Response: Updated paper object

#### Delete Paper

```http
DELETE /papers/1
Authorization: Bearer <token>
```

Note: Only the paper owner can delete.

Response:
```json
{
  "message": "Paper deleted successfully"
}
```

### Search

#### Hybrid Search

```http
GET /papers/search?q=attention%20mechanisms&limit=20
```

Query parameters:
- `q` (required): Search query
- `limit` (optional): Number of results (default: 50)

Response:
```json
{
  "results": [
    {
      "id": 1,
      "title": "Attention Is All You Need",
      "authors": "Vaswani et al.",
      "summary": "Introduces the Transformer...",
      "score": 0.95,
      "user": {
        "username": "john"
      }
    }
  ],
  "query": "attention mechanisms",
  "total": 1
}
```

Note: Always uses hybrid search (FTS5 + vector similarity with RRF). Returns public papers + your private papers (if authenticated).

### Tags

#### List User Tags

```http
GET /tags
Authorization: Bearer <token>
```

Response:
```json
{
  "tags": [
    {"id": 1, "name": "transformers", "count": 5},
    {"id": 2, "name": "attention", "count": 3}
  ]
}
```

#### Tag Autocomplete

```http
GET /tags/autocomplete?q=trans
Authorization: Bearer <token>
```

Response:
```json
{
  "suggestions": ["transformers", "transfer-learning"]
}
```

### Users

#### Get User Profile

```http
GET /users/john
```

Response:
```json
{
  "username": "john",
  "display_name": "John Doe",
  "bio": "ML researcher interested in NLP",
  "created_at": "2024-01-01T00:00:00Z",
  "paper_count": 42
}
```

#### Get User Papers

```http
GET /users/john/papers?limit=20&offset=0
```

Response: Same as `/papers` endpoint, filtered by user

### RSS Feeds

#### Global Feed

```http
GET /feed.xml
```

Returns RSS XML with recent public papers from all users.

#### User Feed

```http
GET /users/john/feed.xml
```

Returns RSS XML with recent public papers from specific user.

### API Keys (Phase 3)

#### Generate API Key

```http
POST /api-keys
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My automation script",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

Response:
```json
{
  "id": 1,
  "key": "pt_1a2b3c4d5e6f7g8h9i0j",
  "name": "My automation script",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

Note: API key is only shown once. Store it securely.

#### List API Keys

```http
GET /api-keys
Authorization: Bearer <token>
```

#### Revoke API Key

```http
DELETE /api-keys/1
Authorization: Bearer <token>
```

## Using API Keys

Once generated, use API key in header instead of JWT:

```http
GET /papers
Authorization: ApiKey pt_1a2b3c4d5e6f7g8h9i0j
```

## Rate Limiting

- Anonymous: 20 requests/minute
- Authenticated: 60 requests/minute
- API keys: Custom limits per key

Rate limit headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642252800
```

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid input: title is required"
}
```

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden

```json
{
  "detail": "You don't have permission to edit this paper"
}
```

### 404 Not Found

```json
{
  "detail": "Paper not found"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

## Example Usage

### Python

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/auth/login",
    data={"username": "john", "password": "password"}
)
token = response.json()["access_token"]

# Create paper
headers = {"Authorization": f"Bearer {token}"}
paper = {
    "title": "Example Paper",
    "authors": "John Doe",
    "summary": "This is a summary",
    "tags": ["example"],
    "paper_url": "https://example.com/paper.pdf"
}
response = requests.post(
    "http://localhost:8000/papers",
    json=paper,
    headers=headers
)
print(response.json())

# Search
response = requests.get(
    "http://localhost:8000/papers/search?q=transformers",
    headers=headers
)
print(response.json())
```

### cURL

```bash
# Login
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -d "username=john&password=password" \
  | jq -r '.access_token')

# Create paper
curl -X POST http://localhost:8000/papers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Example Paper",
    "authors": "John Doe",
    "summary": "This is a summary",
    "tags": ["example"],
    "paper_url": "https://example.com/paper.pdf"
  }'

# Search
curl http://localhost:8000/papers/search?q=transformers \
  -H "Authorization: Bearer $TOKEN"
```

## OpenAPI/Swagger Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
