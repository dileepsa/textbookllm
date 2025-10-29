# Context Management Feature

## Overview

Added functionality to view uploaded files and delete them from the knowledge base.

## Features Implemented

### 1. **Uploaded Files List**

- Displays all uploaded files in the Ingest section
- Shows filename and file type for each document
- Auto-updates when new files are uploaded
- Empty state message when no files are present

### 2. **Delete Functionality**

- Delete button (✕) next to each file
- Confirmation dialog before deletion
- Removes document and all associated chunks from:
  - Metadata store
  - Vector store (ChromaDB)
- Updates all file lists after deletion

## Technical Implementation

### Backend Changes

#### API Endpoints

- `DELETE /documents/{document_id}` - Delete a document

#### New Methods

**VectorStore:**

- `delete(ids: List[str])` - Delete vectors by chunk IDs

**MetadataStore:**

- `delete_document(document_id: str) -> bool` - Delete document and chunks
- `get_chunk_ids_by_document(document_id: str) -> List[str]` - Get all chunk IDs for a document

**Pipeline:**

- `delete_document(document_id: str) -> bool` - Orchestrates deletion from both stores

### Frontend Changes

#### New UI Components

- **Uploaded Files Section** - Shows list of uploaded files with delete buttons
- **Delete Buttons** - Red ✕ button with hover effect
- **Confirmation Dialog** - Native confirm() dialog before deletion

#### JavaScript Functions

- `loadUploadedFilesList()` - Fetches and displays uploaded files
- `deleteDocument(documentId)` - Handles delete API call
- Auto-refresh after upload and delete operations

#### CSS Styling

- `.uploaded-files-section` - Container for uploaded files
- `.uploaded-file-item` - Individual file card with hover effect
- `.delete-btn` - Styled delete button

## User Flow

### Adding Files

1. Upload file via drag-drop or browse
2. File appears in "Uploaded Files" list immediately
3. File also appears in query filter list

### Deleting Files

1. Click ✕ button next to any file
2. Confirm deletion in dialog
3. File removed from all lists
4. Associated vectors and chunks deleted from database
5. Success/error message displayed

## Benefits

✅ **Visibility** - Users can see what files are in the knowledge base  
✅ **Control** - Users can remove unwanted or outdated documents  
✅ **Context Management** - Keep knowledge base clean and relevant  
✅ **Storage Management** - Free up space by removing unnecessary files

## Next Steps

Potential enhancements:

- Bulk delete functionality
- File metadata (size, upload date, chunk count)
- Search/filter uploaded files
- Export document list
- Undo delete functionality
