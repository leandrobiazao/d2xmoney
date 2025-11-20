# Brokerage History - Specification

This document specifies the Brokerage History application for tracking and viewing the history of processed brokerage notes and their extracted operations.

## Overview

The Brokerage History app allows users to:
- View history of all processed brokerage notes
- See details of each processed note (date, number, file name)
- View extracted operations from each note
- Search and filter history by date, user, note number
- Delete processed notes from history
- Prevent duplicate note uploads (same user_id + note_number + note_date)

## Backend Components

### Prompt BH-1: Create Brokerage Note History Storage Service
```
Create JSON file storage service in backend/brokerage_notes/services.py:
- Service name: BrokerageNoteHistoryService
- Methods:
  - get_history_file_path() -> returns path to backend/data/brokerage_notes.json
  - load_history() -> List[dict]: Load all notes from JSON file
  - save_history(notes: List[dict]) -> None: Save notes list to JSON file
  - get_note_by_id(note_id: str) -> dict | None: Get note by ID
  - get_notes_by_user(user_id: str) -> List[dict]: Get all notes for a user
  - add_note(note_data: dict) -> str: Add new note and return ID
  - update_note(note_id: str, note_data: dict) -> None: Update note
  - delete_note(note_id: str) -> None: Delete note from history
  - generate_note_id() -> str: Generate unique UUID for note
- Handle file creation if doesn't exist (initialize with empty list)
- Handle JSON parsing errors gracefully
- Use proper file locking for concurrent access safety
```

### Prompt BH-2: Create Brokerage Note Model Interface
```
Define note data structure:
- id: string (UUID)
- user_id: string
- file_name: string
- original_file_path: string (path to uploaded PDF)
- processed_at: string (ISO datetime)
- note_date: string (date from PDF, DD/MM/YYYY)
- note_number: string (from PDF)
- operations_count: number
- operations: Operation[] (full operation objects)
- status: 'success' | 'partial' | 'failed'
- error_message?: string (if failed)
```

### Prompt BH-3: Create Brokerage Note Serializer
```
Create Django REST Framework serializer in backend/brokerage_notes/serializers.py:
- Serializer name: BrokerageNoteSerializer
- Based on Serializer class
- Fields:
  - id (read-only, UUID string)
  - user_id (CharField, required)
  - file_name (CharField, required)
  - original_file_path (CharField, required)
  - processed_at (DateTimeField, read-only)
  - note_date (CharField, required)
  - note_number (CharField, required)
  - operations_count (IntegerField, read-only)
  - operations (list of Operation dictionaries)
  - status (CharField, choices: ['success', 'partial', 'failed'])
  - error_message (CharField, allow_blank=True, allow_null=True)
```

### Prompt BH-4: Create Brokerage Note API Views
```
Create Django REST Framework views in backend/brokerage_notes/views.py:
- View name: BrokerageNoteListView (APIView)
  - GET: List all notes
    - Accept query parameters: user_id, date_from, date_to, note_number
    - Filter notes based on parameters
    - Load notes from JSON file
    - Return paginated response (optional)
    - Return JSON response with notes array
- View name: BrokerageNoteCreateView (APIView)
  - POST: Create new note entry
    - Accept note data with operations
    - Validate using BrokerageNoteSerializer
    - Generate note ID
    - Add processed_at timestamp
    - Save note to JSON file
    - Return created note with 201 status
- View name: BrokerageNoteDetailView (APIView)
  - GET: Get note by ID
    - Load note from JSON file
    - Return 404 if not found
    - Return full note with operations
  - DELETE: Delete note by ID
    - Load notes from JSON file
    - Remove note from list
    - Optionally delete original PDF file
    - Save updated list to JSON file
    - Return 204 No Content
- Use BrokerageNoteHistoryService for file operations
```

### Prompt BH-5: Create Brokerage Note URLs Configuration
```
Create URL configuration in backend/brokerage_notes/urls.py:
- Import path from django.urls
- Import views from brokerage_notes.views
- URL patterns:
  - path('api/brokerage-notes/', views.BrokerageNoteListView.as_view(), name='note-list')
  - path('api/brokerage-notes/', views.BrokerageNoteCreateView.as_view(), name='note-create')
  - path('api/brokerage-notes/<str:note_id>/', views.BrokerageNoteDetailView.as_view(), name='note-detail')
  - path('api/brokerage-notes/<str:note_id>/operations/', views.BrokerageNoteOperationsView.as_view(), name='note-operations')
- Include in main project URLs (backend/portfolio_api/urls.py):
  - Add: path('', include('brokerage_notes.urls'))
```

## Frontend Components

### Prompt BH-6: Create Brokerage Note Model Interface
```
Create note model interface in frontend/src/app/brokerage-history/note.model.ts:
- Interface name: BrokerageNote
- Properties:
  - id: string
  - user_id: string
  - file_name: string
  - original_file_path: string
  - processed_at: string (ISO datetime)
  - note_date: string (DD/MM/YYYY)
  - note_number: string
  - operations_count: number
  - operations: Operation[]
  - status: 'success' | 'partial' | 'failed'
  - error_message?: string
```

### Prompt BH-7: Create Brokerage History Service
```
Create history service in frontend/src/app/brokerage-history/history.service.ts:
- Service name: BrokerageHistoryService
- Injectable, provided in root
- Methods:
  - getHistory(filters?: HistoryFilters): Observable<BrokerageNote[]>
    - GET request to http://localhost:8000/api/brokerage-notes/
    - Accept query parameters: user_id, date_from, date_to, note_number
    - Return array of notes
  - getNoteById(id: string): Observable<BrokerageNote>
    - GET request to http://localhost:8000/api/brokerage-notes/{id}/
    - Return single note with operations
  - addNote(note: BrokerageNote): Observable<BrokerageNote>
    - POST request to http://localhost:8000/api/brokerage-notes/
    - Accept note data with operations
    - Return created note
  - deleteNote(id: string): Observable<void>
    - DELETE request to http://localhost:8000/api/brokerage-notes/{id}/
    - Return void on success
- Use HttpClient from @angular/common/http
- Handle errors with proper error messages
```

### Prompt BH-8: Create History List Component
```
Create history list component in frontend/src/app/brokerage-history/history-list/:
- Component name: HistoryListComponent
- Standalone component
- Display list of all processed notes
- Filters:
  - User selector (dropdown)
  - Date range picker (from/to)
  - Note number search
- Table columns:
  - Date (note_date)
  - Note Number
  - File Name
  - Operations Count
  - Status (with badge/icon)
  - Processed At
  - Actions (view, delete)
- Load history on component initialization
- Use BrokerageHistoryService.getHistory()
- Handle loading and error states
- Refresh after note deletion
- Clickable rows to view note details
```

### Prompt BH-9: Create History Detail Component
```
Create history detail component in frontend/src/app/brokerage-history/history-detail/:
- Component name: HistoryDetailComponent
- Standalone component
- Input: noteId (route parameter)
- Display note metadata:
  - File name
  - Note date
  - Note number
  - Processed at timestamp
  - Status badge
  - Error message (if failed)
- Display operations table:
  - All extracted operations from the note
  - Columns: Título, Tipo, Quantidade, Preço, Valor, Data
  - Format currency as BRL
  - Color code by operation type (buy/sell)
- "Back to List" button
- "Delete Note" button (with confirmation)
- Load note details on component initialization
- Use BrokerageHistoryService.getNoteById()
```

### Prompt BH-10: Create History Filters Component
```
Create filters component in frontend/src/app/brokerage-history/history-filters/:
- Component name: HistoryFiltersComponent
- Standalone component
- Output: filtersChange event emitter
- Filter controls:
  - User selector (dropdown, optional)
  - Date from input (optional)
  - Date to input (optional)
  - Note number search input (optional)
- "Apply Filters" button
- "Clear Filters" button
- Emit filters when changed
- Display active filter count badge
```

### Prompt BH-11: Create History Summary Card Component
```
Create summary card component in frontend/src/app/brokerage-history/history-summary/:
- Component name: HistorySummaryComponent
- Standalone component
- Input: notes (BrokerageNote[])
- Display summary statistics:
  - Total notes processed
  - Total operations extracted
  - Success rate percentage
  - Date range of notes
  - Most active user (if multiple users)
- Update when notes list changes
```

## Integration with Brokerage Note Processing

### Prompt BH-12: Integrate History Tracking
```
Update UploadPdfComponent in brokerage note processing:
- After successful PDF parsing:
  - Create BrokerageNote object with:
    - user_id (from clientId)
    - file_name (from uploaded file)
    - original_file_path (save file to backend/media/brokerage_notes/)
    - processed_at (current timestamp)
    - note_date (extracted from PDF)
    - note_number (extracted from PDF)
    - operations_count (from parsed operations)
    - operations (full operation array)
    - status ('success' or 'partial' based on operations found)
  - Call BrokerageHistoryService.addNote()
  - Show success message with link to view in history
```

## API Endpoints

### GET /api/brokerage-notes/
**Description**: List all processed brokerage notes

**Query Parameters**:
- user_id (optional): Filter by user ID
- date_from (optional): Filter notes from date (YYYY-MM-DD)
- date_to (optional): Filter notes to date (YYYY-MM-DD)
- note_number (optional): Search by note number

**Response** (200 OK):
```json
[
  {
    "id": "uuid-string",
    "user_id": "user-uuid",
    "file_name": "nota_setembro_2025.pdf",
    "original_file_path": "/media/brokerage_notes/uuid_nota_setembro_2025.pdf",
    "processed_at": "2025-11-05T12:00:00Z",
    "note_date": "01/09/2025",
    "note_number": "123456789",
    "operations_count": 5,
    "operations": [...],
    "status": "success"
  }
]
```

### POST /api/brokerage-notes/
**Description**: Create new note entry in history

**Request Body**:
```json
{
  "user_id": "user-uuid",
  "file_name": "nota_setembro_2025.pdf",
  "original_file_path": "/media/brokerage_notes/uuid_nota_setembro_2025.pdf",
  "note_date": "01/09/2025",
  "note_number": "123456789",
  "operations": [...],
  "status": "success"
}
```

**Response** (201 Created): Created note object

**Error Response** (409 Conflict - Duplicate Note):
```json
{
  "error": "Nota de corretagem já processada",
  "message": "A nota número 123456789 de 01/09/2025 já foi processada anteriormente.",
  "existing_note_id": "uuid-of-existing-note",
  "existing_note": {...}
}
```

**Duplicate Detection**: Notes are considered duplicates if they have the same `user_id`, `note_number`, and `note_date`. The system prevents uploading the same brokerage note twice to avoid duplicate operations in the portfolio.

### GET /api/brokerage-notes/{note_id}/
**Description**: Get note details by ID

**Response** (200 OK): Full note object with operations

**Error Response** (404 Not Found):
```json
{
  "error": "Note not found"
}
```

### GET /api/brokerage-notes/{note_id}/operations/
**Description**: Get operations from a specific note

**Response** (200 OK):
```json
{
  "note_id": "uuid-string",
  "operations": [...]
}
```

### DELETE /api/brokerage-notes/{note_id}/
**Description**: Delete note from history

**Response** (204 No Content)

**Error Response** (404 Not Found): Note not found

## Data Storage

- **Brokerage Notes History**: Database storage (SQLite) in `brokerage_notes` and `operations` tables
- **Note PDFs**: File storage at `backend/media/brokerage_notes/`

**Note**: The system has migrated from JSON file storage to SQLite database. All brokerage note data is now stored in the database with proper relationships and constraints. See [09-database-data-model.md](09-database-data-model.md) for complete database schema.
- File format: `{note_id}_{original_filename}`

## Integration

### Integrate into Main App
```
Update main app routing:
- Add route for history list: /brokerage-history
- Add route for history detail: /brokerage-history/:id
- Add navigation link to history in header/menu
- Integrate with brokerage note processing to save history after upload
```

---

**Related Documents**:  
- [Main Specification](README.md)  
- [Brokerage Note Processing](02-brokerage-note-processing.md)  
- [Portfolio Summary](04-portfolio-summary.md)

