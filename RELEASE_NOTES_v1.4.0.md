# Release Notes - Version 1.4.0

**Release Date:** November 22, 2025

> For general features and setup, see the main [README.md](README.md). This release and tag (`v1.4.0`) have been published and all live documentation reflects the new version. All version numbers, navigation menus, and UI badges now display 1.4.0.

---

## New Features

### MinIO File Manager

A comprehensive file management interface has been added to the web portal, providing a complete solution for managing files in MinIO object storage.

#### Key Features

1. **File Upload**
   - Simple file picker interface
   - Optional path/prefix support for organizing files in folders
   - Real-time upload status feedback
   - Automatic bucket creation on first upload

2. **File Browsing**
   - Dual view modes: Table view (compact) and Grid view (visual cards)
   - View toggle buttons for easy switching
   - File filtering by prefix/path
   - File type detection and appropriate icons

3. **File Operations**
   - **Download**: Direct file download via browser
   - **Delete**: Confirmation dialog before deletion
   - **Preview**: Built-in preview for images and text files
   - **Metadata**: View detailed file information (size, type, last modified)

4. **User Interface**
   - Clean, modern design consistent with existing portal pages
   - Responsive layout works on desktop and mobile
   - Modal dialogs for preview and metadata
   - Loading states and error handling
   - Empty state messaging when no files exist

#### Technical Implementation

**New Files Created:**
- `src/web/routes/files.py` - Route handler for the file manager page
- `src/web/templates/files.html` - HTML template with dual-view layout
- `src/web/static/js/files.js` - JavaScript for API integration and interactions

**Files Modified:**
- `src/web/app.py` - Registered files router, updated version to 1.4.0
- `src/web/templates/base.html` - Added "Files" link to navigation menu, updated version
- `src/web/static/css/style.css` - Added comprehensive styling for file manager
- `src/web/routes/home.py` - Updated version to 1.4.0

#### API Integration

The file manager uses the existing API endpoints:
- `GET /api/files/` - List files in bucket with optional prefix filtering
- `POST /api/files/upload` - Upload file to specified bucket and key
- `GET /api/files/{key}` - Download file
- `DELETE /api/files/{key}` - Delete file

**Default Configuration:**
- Default bucket: `odin-files`
- Bucket is automatically created on first upload if it doesn't exist
- All file operations go through the API service

#### Usage

1. Navigate to **Files** in the main navigation menu
2. Upload files using the upload form (with optional folder path)
3. Browse files in table or grid view
4. Use the filter to search by prefix/folder
5. Click action buttons to preview, download, view info, or delete files

#### Preview Support

The file manager can preview:
- **Images**: jpg, jpeg, png, gif, webp, bmp, svg (displayed in modal)
- **Text files**: txt, json, xml, csv, md, log, yml, yaml (displayed with syntax)

Other file types can be downloaded but not previewed in the browser.

## Version Updates

All version references have been updated from 1.2.0/1.3.0 to 1.4.0:
- Web application version
- Footer version display
- Home page version context

## Architecture Notes

The implementation follows SOLID principles and the existing codebase patterns:
- **Single Responsibility**: Each file has a clear, focused purpose
- **API-First Design**: All operations go through the REST API
- **Separation of Concerns**: Backend routes, templates, JavaScript, and CSS are cleanly separated
- **Consistent Patterns**: Follows the same structure as existing features (Image Analyzer, Logs)
- **Type Safety**: Python code includes full type hints
- **Error Handling**: Comprehensive error handling with user-friendly messages

## Testing

To test the file manager:

1. Start the application with `docker-compose up`
2. Navigate to http://localhost/files
3. Upload a test file
4. Verify file appears in the list
5. Test download, preview (for images/text), and delete operations
6. Test view toggle between table and grid
7. Test prefix filtering

## Future Enhancements

Potential improvements for future versions:
- Drag-and-drop file upload
- Bulk file operations (select multiple files)
- File search functionality
- Sort by name, size, or date
- Folder/directory tree view
- File sharing with temporary URLs
- Upload progress bar
- Thumbnail generation for images

---

For more information about the Odin project, see the main [README.md](README.md).

