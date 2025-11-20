# User Management - Specification

This document specifies the User Management application for creating and managing users with CPF, account provider, account number, and profile pictures.

## Overview

The User Management app allows users to:
- Create new users with complete information
- View list of all users
- Update user information
- Delete users
- Upload and manage user profile pictures

## Backend Components

### Prompt UM-1: Create Users Django App
```
Create a new Django app for user management:
- Navigate to backend/ directory
- Run: python manage.py startapp users
- Register app in INSTALLED_APPS: 'users'
- App structure:
  - backend/users/
    ├── __init__.py
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── serializers.py (create new file)
    ├── services.py (create new file for JSON file operations)
    └── admin.py
```

### Prompt UM-2: Create User JSON Storage Service
```
Create JSON file storage service in backend/users/services.py:
- Service name: UserJsonStorageService
- Methods:
  - get_users_file_path() -> returns path to backend/data/users.json
  - load_users() -> List[dict]: Load all users from JSON file
  - save_users(users: List[dict]) -> None: Save users list to JSON file
  - get_user_by_id(user_id: str) -> dict | None: Get user by ID
  - user_exists(user_id: str) -> bool: Check if user exists
  - generate_user_id() -> str: Generate unique UUID for user
- Handle file creation if doesn't exist (initialize with empty list)
- Handle JSON parsing errors gracefully
- Use proper file locking for concurrent access safety
- Return empty list if file doesn't exist or is empty
```

### Prompt UM-3: Create User Serializer
```
Create Django REST Framework serializer in backend/users/serializers.py:
- Serializer name: UserSerializer
- Based on Serializer class (not ModelSerializer since we're using JSON files)
- Fields:
  - id (read-only, UUID string)
  - name (CharField, required, max_length=200)
  - cpf (CharField, required, max_length=14)
  - account_provider (CharField, required, max_length=100)
  - account_number (CharField, required, max_length=50)
  - picture (ImageField, required, allow_null=True)
  - created_at (DateTimeField, read-only)
  - updated_at (DateTimeField, read-only)
- Validation:
  - CPF format: Validate Brazilian CPF format (XXX.XXX.XXX-XX or numbers only)
  - CPF digits: Validate CPF checksum algorithm
  - CPF uniqueness: CPF must be unique across all users (no duplicate CPF allowed)
  - Account number: Validate format (alphanumeric)
  - Account number uniqueness: Account number must be unique across all users (no duplicate account number allowed)
  - Picture: Validate file type (image/jpeg, image/png, image/jpg)
  - Picture size: Max 5MB
- Custom methods:
  - validate_cpf: Clean and validate CPF format
  - validate_picture: Validate image file
```

### Prompt UM-4: Create User API Views
```
Create Django REST Framework views in backend/users/views.py:
- View name: UserListView (APIView)
  - GET: List all users
    - Load users from JSON file
    - Return paginated response (optional)
    - Return JSON response with users array
- View name: UserCreateView (APIView)
  - POST: Create new user
    - Validate request data using UserSerializer
    - Handle picture file upload
    - Save picture to backend/media/users/{user_id}_{filename}
    - Generate unique user ID (UUID)
    - Add created_at and updated_at timestamps
    - Save user to JSON file
    - Return created user with 201 status
    - Handle validation errors (400)
- View name: UserDetailView (APIView)
  - GET: Get user by ID
    - Load user from JSON file
    - Return 404 if not found
    - Return user JSON
  - PUT: Update user by ID
    - Load user from JSON file
    - Update fields (preserve picture if not provided)
    - Handle picture update if provided
    - Update updated_at timestamp
    - Save to JSON file
    - Return updated user
  - DELETE: Delete user by ID
    - Load users from JSON file
    - Remove user from list
    - Delete picture file if exists
    - Save updated list to JSON file
    - Return 204 No Content
- Import necessary modules: os, json, uuid, pathlib
- Use UserJsonStorageService for file operations
```

### Prompt UM-5: Create User URLs Configuration
```
Create URL configuration in backend/users/urls.py:
- Import path from django.urls
- Import views from users.views
- URL patterns:
  - path('api/users/', views.UserListView.as_view(), name='user-list')
  - path('api/users/', views.UserCreateView.as_view(), name='user-create')
  - path('api/users/<str:user_id>/', views.UserDetailView.as_view(), name='user-detail')
- Include in main project URLs (backend/portfolio_api/urls.py):
  - Add: path('', include('users.urls'))
```

## Frontend Components

### Prompt UM-6: Create User Model Interface
```
Create user model interface in frontend/src/app/users/user.model.ts:
- Interface name: User
- Properties:
  - id: string
  - name: string
  - cpf: string
  - account_provider: string
  - account_number: string
  - picture: string (URL or file path)
  - created_at?: string (ISO date, optional)
  - updated_at?: string (ISO date, optional)
```

### Prompt UM-7: Create User Service
```
Create user service in frontend/src/app/users/user.service.ts:
- Service name: UserService
- Injectable, provided in root
- Methods:
  - getUsers(): Observable<User[]>
    - GET request to http://localhost:8000/api/users/
    - Return array of users
  - getUserById(id: string): Observable<User>
    - GET request to http://localhost:8000/api/users/{id}/
    - Return single user
  - createUser(userData: FormData): Observable<User>
    - POST request to http://localhost:8000/api/users/
    - Accept FormData with user fields and picture file
    - Return created user
  - updateUser(id: string, userData: FormData): Observable<User>
    - PUT request to http://localhost:8000/api/users/{id}/
    - Accept FormData with user fields and optional picture file
    - Return updated user
  - deleteUser(id: string): Observable<void>
    - DELETE request to http://localhost:8000/api/users/{id}/
    - Return void on success
- Use HttpClient from @angular/common/http
- Handle errors with proper error messages
- Return Observable for async operations
```

### Prompt UM-8: Create User Creation Form Component
```
Create user creation form component in frontend/src/app/users/create-user/:
- Component name: CreateUserComponent
- Standalone component
- Form fields with validation:
  - Name (text input, required, min 3 characters)
  - CPF (text input, required, CPF format validation)
  - Account Provider (text input, required)
  - Account Number (text input, required, alphanumeric)
  - Picture (file input, required, accept: image/jpeg, image/png, image/jpg)
- Form validation:
  - CPF format: XXX.XXX.XXX-XX
  - CPF validation using Brazilian CPF algorithm
  - Picture preview before upload
  - File size validation (max 5MB)
  - File type validation
- Submit button: "Create User"
- Cancel button: "Cancel"
- On submit:
  - Create FormData object
  - Append all fields including picture file
  - Call UserService.createUser()
  - Show success message
  - Emit event to parent or navigate
  - Reset form
- On cancel: Emit close event or navigate back
- Display form in modal/dialog or dedicated page
- Show loading state during submission
- Display error messages for validation failures
```

### Prompt UM-9: Create User List Component
```
Create user list component in frontend/src/app/users/user-list/:
- Component name: UserListComponent
- Standalone component
- Display list of all users
- "Create New User" button
- Load users on component initialization
- Use UserService.getUsers()
- Display users in grid or list layout
- Show user picture, name, CPF, account provider
- Clickable to select user (emit selection event)
- Handle empty state (no users)
- Handle loading and error states
- Refresh after user creation
```

### Prompt UM-10: Create User Item Component
```
Create user item component in frontend/src/app/users/user-item/:
- Component name: UserItemComponent
- Standalone component
- Input: user (User model)
- Input: selected (boolean)
- Output: select event emitter
- Display user avatar/picture and name
- Show selected/active state visually
- Clickable to select user
- Display user details on hover
```

### Prompt UM-11: Add CPF Validation Utility
```
Create CPF validation utility in frontend/src/app/shared/utils/cpf-validator.ts:
- Function: validateCPF(cpf: string): boolean
  - Remove formatting (dots, dashes)
  - Validate length (11 digits)
  - Validate Brazilian CPF checksum algorithm
  - Return true if valid, false otherwise
- Function: formatCPF(cpf: string): string
  - Format CPF as XXX.XXX.XXX-XX
  - Handle partial input
- Export both functions
- Use in CreateUserComponent form validation
```

### Prompt UM-12: Add Picture Upload Preview Component
```
Create picture preview component in frontend/src/app/users/picture-preview/:
- Component name: PicturePreviewComponent
- Standalone component
- Input: file (File object)
- Display image preview before upload
- Show file name and size
- Validate file type and size
- Display error if invalid
- Allow user to change/remove picture
- Use FileReader API for preview
- Display preview in thumbnail format
```

## API Endpoints

### GET /api/users/
**Description**: List all users

**Response** (200 OK):
```json
[
  {
    "id": "uuid-string",
    "name": "John Doe",
    "cpf": "123.456.789-00",
    "account_provider": "XP Investimentos",
    "account_number": "12345-6",
    "picture": "/media/users/uuid_string_filename.jpg",
    "created_at": "2025-11-05T12:00:00Z",
    "updated_at": "2025-11-05T12:00:00Z"
  }
]
```

### POST /api/users/
**Description**: Create a new user

**Request**: multipart/form-data
- name (string, required)
- cpf (string, required, format: XXX.XXX.XXX-XX, must be unique)
- account_provider (string, required)
- account_number (string, required, must be unique)
- picture (file, required, image/jpeg, image/png, image/jpg, max 5MB)

**Response** (201 Created):
```json
{
  "id": "uuid-string",
  "name": "John Doe",
  "cpf": "123.456.789-00",
  "account_provider": "XP Investimentos",
  "account_number": "12345-6",
  "picture": "/media/users/uuid_string_filename.jpg",
  "created_at": "2025-11-05T12:00:00Z",
  "updated_at": "2025-11-05T12:00:00Z"
}
```

**Error Response** (400 Bad Request):
```json
{
  "error": "Validation error",
  "details": {
    "cpf": ["Invalid CPF format"],
    "picture": ["File size exceeds 5MB"]
  }
}
```

**Error Response** (400 Bad Request - Uniqueness):
```json
{
  "error": "Validation error",
  "details": {
    "cpf": ["CPF já cadastrado"]
  }
}
```

or

```json
{
  "error": "Validation error",
  "details": {
    "account_number": ["Número da conta já cadastrado"]
  }
}
```

### GET /api/users/{user_id}/
**Description**: Get user by ID

**Response** (200 OK): User object (same format as POST response)

**Error Response** (404 Not Found):
```json
{
  "error": "User not found"
}
```

### PUT /api/users/{user_id}/
**Description**: Update user by ID

**Request**: multipart/form-data (all fields optional except those being updated)

**Response** (200 OK): Updated user object

**Error Response** (404 Not Found): User not found  
**Error Response** (400 Bad Request): Validation errors

### DELETE /api/users/{user_id}/
**Description**: Delete user by ID

**Response** (204 No Content)

**Error Response** (404 Not Found): User not found

## Data Storage

- **Users**: Database storage (SQLite) in `users` table
- **User Pictures**: File storage at `backend/media/users/`
- File format: `{user_id}_{original_filename}`

**Note**: The system has migrated from JSON file storage to SQLite database. All user data is now stored in the database with proper relationships and constraints. See [09-database-data-model.md](09-database-data-model.md) for complete database schema.

## Integration

### Integrate into Main App
```
Update main app component in frontend/src/app/:
- Load users from UserService on initialization
- Display UserListComponent
- Add "Create User" button/menu item
- Navigate to CreateUserComponent or show modal
- Handle user selection with new user structure
- Pass selected user to other components (portfolio, etc.)
```

---

**Related Documents**:  
- [Main Specification](README.md)  
- [Brokerage Note Processing](02-brokerage-note-processing.md)  
- [Portfolio Summary](04-portfolio-summary.md)

