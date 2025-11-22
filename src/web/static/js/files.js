/**
 * File Manager JavaScript
 * Handles file upload, download, delete, preview, and view switching
 */

document.addEventListener('DOMContentLoaded', function () {
  // API Configuration
  const API_BASE_URL = '/api';
  const DEFAULT_BUCKET = 'odin-files';
  
  // State
  let currentView = 'table'; // 'table' or 'grid'
  let currentPrefix = '';
  let fileToDelete = null;
  
  // DOM Elements
  const uploadForm = document.getElementById('upload-form');
  const fileInput = document.getElementById('file-input');
  const fileNameSpan = document.getElementById('file-name');
  const filePathInput = document.getElementById('file-path');
  const uploadStatus = document.getElementById('upload-status');
  
  const refreshBtn = document.getElementById('refresh-btn');
  const prefixFilter = document.getElementById('prefix-filter');
  const applyFilterBtn = document.getElementById('apply-filter-btn');
  const clearFilterBtn = document.getElementById('clear-filter-btn');
  
  const viewTableBtn = document.getElementById('view-table');
  const viewGridBtn = document.getElementById('view-grid');
  
  const loadingState = document.getElementById('loading');
  const tableView = document.getElementById('table-view');
  const gridView = document.getElementById('grid-view');
  const errorState = document.getElementById('error-state');
  const tableBody = document.getElementById('table-body');
  const gridContainer = document.getElementById('grid-container');
  const tableEmpty = document.getElementById('table-empty');
  const gridEmpty = document.getElementById('grid-empty');
  
  // Modals
  const previewModal = document.getElementById('preview-modal');
  const previewTitle = document.getElementById('preview-title');
  const previewBody = document.getElementById('preview-body');
  const previewClose = document.getElementById('preview-close');
  
  const metadataModal = document.getElementById('metadata-modal');
  const metadataBody = document.getElementById('metadata-body');
  const metadataClose = document.getElementById('metadata-close');
  
  const deleteModal = document.getElementById('delete-modal');
  const deleteFilename = document.getElementById('delete-filename');
  const deleteClose = document.getElementById('delete-close');
  const deleteCancel = document.getElementById('delete-cancel');
  const deleteConfirm = document.getElementById('delete-confirm');
  
  // Initialize
  loadFiles();
  
  // Event Listeners
  fileInput.addEventListener('change', function() {
    if (fileInput.files.length > 0) {
      fileNameSpan.textContent = fileInput.files[0].name;
    } else {
      fileNameSpan.textContent = '';
    }
  });
  
  uploadForm.addEventListener('submit', handleUpload);
  refreshBtn.addEventListener('click', () => loadFiles());
  applyFilterBtn.addEventListener('click', handleApplyFilter);
  clearFilterBtn.addEventListener('click', handleClearFilter);
  
  viewTableBtn.addEventListener('click', () => switchView('table'));
  viewGridBtn.addEventListener('click', () => switchView('grid'));
  
  // Modal close handlers
  previewClose.addEventListener('click', () => closeModal(previewModal));
  metadataClose.addEventListener('click', () => closeModal(metadataModal));
  deleteClose.addEventListener('click', () => closeModal(deleteModal));
  deleteCancel.addEventListener('click', () => closeModal(deleteModal));
  deleteConfirm.addEventListener('click', handleDeleteConfirm);
  
  // Close modals on outside click
  window.addEventListener('click', function(e) {
    if (e.target === previewModal) closeModal(previewModal);
    if (e.target === metadataModal) closeModal(metadataModal);
    if (e.target === deleteModal) closeModal(deleteModal);
  });
  
  // Close modals on escape key
  window.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeModal(previewModal);
      closeModal(metadataModal);
      closeModal(deleteModal);
    }
  });
  
  /**
   * Load files from MinIO
   */
  async function loadFiles() {
    console.log('Loading files from bucket:', DEFAULT_BUCKET, 'prefix:', currentPrefix);
    
    showLoading();
    
    try {
      const url = `${API_BASE_URL}/files/?bucket=${DEFAULT_BUCKET}&prefix=${encodeURIComponent(currentPrefix)}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to load files: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Loaded files:', data);
      
      displayFiles(data.files);
    } catch (error) {
      console.error('Error loading files:', error);
      showError('Failed to load files: ' + error.message);
    }
  }
  
  /**
   * Display files in current view
   */
  function displayFiles(files) {
    hideLoading();
    errorState.style.display = 'none';
    
    if (files.length === 0) {
      tableEmpty.style.display = 'block';
      gridEmpty.style.display = 'block';
      tableBody.innerHTML = '';
      gridContainer.innerHTML = '';
      return;
    }
    
    tableEmpty.style.display = 'none';
    gridEmpty.style.display = 'none';
    
    // Clear existing content
    tableBody.innerHTML = '';
    gridContainer.innerHTML = '';
    
    // Render files in both views
    files.forEach(filename => {
      renderTableRow(filename);
      renderGridCard(filename);
    });
    
    // Show current view
    if (currentView === 'table') {
      tableView.style.display = 'block';
      gridView.style.display = 'none';
    } else {
      tableView.style.display = 'none';
      gridView.style.display = 'block';
    }
  }
  
  /**
   * Render file in table view
   */
  function renderTableRow(filename) {
    const row = document.createElement('tr');
    
    const fileInfo = getFileInfo(filename);
    
    row.innerHTML = `
      <td class="file-name-cell">
        <span class="file-icon">${fileInfo.icon}</span>
        <span class="file-name">${escapeHtml(filename)}</span>
      </td>
      <td>${fileInfo.sizeDisplay}</td>
      <td>${fileInfo.type}</td>
      <td class="actions-cell">
        <button class="btn-action btn-preview" title="Preview">👁</button>
        <button class="btn-action btn-download" title="Download">⬇</button>
        <button class="btn-action btn-info" title="Info">ℹ</button>
        <button class="btn-action btn-delete" title="Delete">🗑</button>
      </td>
    `;
    
    // Attach event listeners
    const previewBtn = row.querySelector('.btn-preview');
    const downloadBtn = row.querySelector('.btn-download');
    const infoBtn = row.querySelector('.btn-info');
    const deleteBtn = row.querySelector('.btn-delete');
    
    if (fileInfo.previewable) {
      previewBtn.addEventListener('click', () => handlePreview(filename));
    } else {
      previewBtn.disabled = true;
      previewBtn.style.opacity = '0.3';
      previewBtn.title = 'Preview not available';
    }
    
    downloadBtn.addEventListener('click', () => handleDownload(filename));
    infoBtn.addEventListener('click', () => handleMetadata(filename));
    deleteBtn.addEventListener('click', () => handleDelete(filename));
    
    tableBody.appendChild(row);
  }
  
  /**
   * Render file in grid view
   */
  function renderGridCard(filename) {
    const card = document.createElement('div');
    card.className = 'file-card';
    
    const fileInfo = getFileInfo(filename);
    
    card.innerHTML = `
      <div class="file-card-preview">
        ${fileInfo.isImage ? 
          `<img src="${API_BASE_URL}/files/${encodeURIComponent(filename)}?bucket=${DEFAULT_BUCKET}" alt="${escapeHtml(filename)}" loading="lazy">` :
          `<div class="file-card-icon">${fileInfo.icon}</div>`
        }
      </div>
      <div class="file-card-info">
        <div class="file-card-name" title="${escapeHtml(filename)}">${escapeHtml(filename)}</div>
        <div class="file-card-meta">${fileInfo.type} • ${fileInfo.sizeDisplay}</div>
      </div>
      <div class="file-card-actions">
        <button class="btn-action btn-preview" title="Preview">👁</button>
        <button class="btn-action btn-download" title="Download">⬇</button>
        <button class="btn-action btn-info" title="Info">ℹ</button>
        <button class="btn-action btn-delete" title="Delete">🗑</button>
      </div>
    `;
    
    // Attach event listeners
    const previewBtn = card.querySelector('.btn-preview');
    const downloadBtn = card.querySelector('.btn-download');
    const infoBtn = card.querySelector('.btn-info');
    const deleteBtn = card.querySelector('.btn-delete');
    
    if (fileInfo.previewable) {
      previewBtn.addEventListener('click', () => handlePreview(filename));
    } else {
      previewBtn.disabled = true;
      previewBtn.style.opacity = '0.3';
      previewBtn.title = 'Preview not available';
    }
    
    downloadBtn.addEventListener('click', () => handleDownload(filename));
    infoBtn.addEventListener('click', () => handleMetadata(filename));
    deleteBtn.addEventListener('click', () => handleDelete(filename));
    
    gridContainer.appendChild(card);
  }
  
  /**
   * Get file information
   */
  function getFileInfo(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    
    const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'];
    const textExts = ['txt', 'json', 'xml', 'csv', 'md', 'log', 'yml', 'yaml'];
    const docExts = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'];
    const codeExts = ['js', 'py', 'java', 'cpp', 'c', 'h', 'html', 'css', 'ts', 'go', 'rs'];
    
    const isImage = imageExts.includes(ext);
    const isText = textExts.includes(ext);
    const isDoc = docExts.includes(ext);
    const isCode = codeExts.includes(ext);
    
    let icon = '📄';
    let type = 'File';
    
    if (isImage) {
      icon = '🖼';
      type = 'Image';
    } else if (isText) {
      icon = '📝';
      type = 'Text';
    } else if (isDoc) {
      icon = '📋';
      type = 'Document';
    } else if (isCode) {
      icon = '💻';
      type = 'Code';
    } else if (ext === 'zip' || ext === 'tar' || ext === 'gz') {
      icon = '📦';
      type = 'Archive';
    } else if (ext === 'mp4' || ext === 'avi' || ext === 'mov') {
      icon = '🎬';
      type = 'Video';
    } else if (ext === 'mp3' || ext === 'wav' || ext === 'ogg') {
      icon = '🎵';
      type = 'Audio';
    }
    
    return {
      icon,
      type,
      isImage,
      isText,
      previewable: isImage || isText,
      sizeDisplay: 'Unknown' // Size not provided by list endpoint
    };
  }
  
  /**
   * Handle file upload
   */
  async function handleUpload(e) {
    e.preventDefault();
    
    if (!fileInput.files || fileInput.files.length === 0) {
      showUploadStatus('Please select a file', 'error');
      return;
    }
    
    const file = fileInput.files[0];
    const prefix = filePathInput.value.trim();
    const key = prefix ? `${prefix}${file.name}` : file.name;
    
    console.log('Uploading file:', file.name, 'as key:', key);
    
    showUploadStatus('Uploading...', 'loading');
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const url = `${API_BASE_URL}/files/upload?bucket=${DEFAULT_BUCKET}&key=${encodeURIComponent(key)}`;
      const response = await fetch(url, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Upload failed: ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('Upload successful:', result);
      
      showUploadStatus(`✓ File uploaded successfully: ${key}`, 'success');
      
      // Reset form
      uploadForm.reset();
      fileNameSpan.textContent = '';
      
      // Reload files
      setTimeout(() => loadFiles(), 500);
      
    } catch (error) {
      console.error('Upload error:', error);
      showUploadStatus(`✗ Upload failed: ${error.message}`, 'error');
    }
  }
  
  /**
   * Handle file download
   */
  function handleDownload(filename) {
    console.log('Downloading file:', filename);
    const url = `${API_BASE_URL}/files/${encodeURIComponent(filename)}?bucket=${DEFAULT_BUCKET}`;
    window.open(url, '_blank');
  }
  
  /**
   * Handle file preview
   */
  async function handlePreview(filename) {
    console.log('Previewing file:', filename);
    
    const fileInfo = getFileInfo(filename);
    
    previewTitle.textContent = filename;
    previewBody.innerHTML = '<p class="loading">Loading preview...</p>';
    openModal(previewModal);
    
    try {
      if (fileInfo.isImage) {
        const url = `${API_BASE_URL}/files/${encodeURIComponent(filename)}?bucket=${DEFAULT_BUCKET}`;
        previewBody.innerHTML = `<img src="${url}" alt="${escapeHtml(filename)}" style="max-width: 100%; height: auto;">`;
      } else if (fileInfo.isText) {
        const url = `${API_BASE_URL}/files/${encodeURIComponent(filename)}?bucket=${DEFAULT_BUCKET}`;
        const response = await fetch(url);
        
        if (!response.ok) {
          throw new Error(`Failed to load file: ${response.statusText}`);
        }
        
        const text = await response.text();
        previewBody.innerHTML = `<pre class="text-preview">${escapeHtml(text)}</pre>`;
      }
    } catch (error) {
      console.error('Preview error:', error);
      previewBody.innerHTML = `<p class="error">Failed to load preview: ${error.message}</p>`;
    }
  }
  
  /**
   * Handle file metadata view
   */
  async function handleMetadata(filename) {
    console.log('Showing metadata for:', filename);
    
    metadataBody.innerHTML = '<p class="loading">Loading metadata...</p>';
    openModal(metadataModal);
    
    try {
      // Fetch file to get headers
      const url = `${API_BASE_URL}/files/${encodeURIComponent(filename)}?bucket=${DEFAULT_BUCKET}`;
      const response = await fetch(url, { method: 'HEAD' });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch metadata: ${response.statusText}`);
      }
      
      const contentLength = response.headers.get('Content-Length');
      const contentType = response.headers.get('Content-Type');
      const lastModified = response.headers.get('Last-Modified');
      
      const sizeBytes = parseInt(contentLength) || 0;
      const sizeKB = (sizeBytes / 1024).toFixed(2);
      const sizeMB = (sizeBytes / (1024 * 1024)).toFixed(2);
      
      metadataBody.innerHTML = `
        <div class="metadata-list">
          <div class="metadata-item">
            <span class="metadata-label">Filename:</span>
            <span class="metadata-value">${escapeHtml(filename)}</span>
          </div>
          <div class="metadata-item">
            <span class="metadata-label">Bucket:</span>
            <span class="metadata-value">${DEFAULT_BUCKET}</span>
          </div>
          <div class="metadata-item">
            <span class="metadata-label">Size:</span>
            <span class="metadata-value">${sizeBytes.toLocaleString()} bytes (${sizeKB} KB / ${sizeMB} MB)</span>
          </div>
          <div class="metadata-item">
            <span class="metadata-label">Content Type:</span>
            <span class="metadata-value">${contentType || 'Unknown'}</span>
          </div>
          <div class="metadata-item">
            <span class="metadata-label">Last Modified:</span>
            <span class="metadata-value">${lastModified || 'Unknown'}</span>
          </div>
          <div class="metadata-item">
            <span class="metadata-label">Full Path:</span>
            <span class="metadata-value code">${DEFAULT_BUCKET}/${filename}</span>
          </div>
        </div>
      `;
    } catch (error) {
      console.error('Metadata error:', error);
      metadataBody.innerHTML = `<p class="error">Failed to load metadata: ${error.message}</p>`;
    }
  }
  
  /**
   * Handle file delete (show confirmation)
   */
  function handleDelete(filename) {
    console.log('Delete requested for:', filename);
    fileToDelete = filename;
    deleteFilename.textContent = filename;
    openModal(deleteModal);
  }
  
  /**
   * Handle delete confirmation
   */
  async function handleDeleteConfirm() {
    if (!fileToDelete) return;
    
    console.log('Deleting file:', fileToDelete);
    
    try {
      const url = `${API_BASE_URL}/files/${encodeURIComponent(fileToDelete)}?bucket=${DEFAULT_BUCKET}`;
      const response = await fetch(url, { method: 'DELETE' });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Delete failed: ${response.statusText}`);
      }
      
      console.log('File deleted successfully');
      closeModal(deleteModal);
      fileToDelete = null;
      
      // Reload files
      loadFiles();
      
    } catch (error) {
      console.error('Delete error:', error);
      alert(`Failed to delete file: ${error.message}`);
    }
  }
  
  /**
   * Handle filter apply
   */
  function handleApplyFilter() {
    currentPrefix = prefixFilter.value.trim();
    console.log('Applying prefix filter:', currentPrefix);
    loadFiles();
  }
  
  /**
   * Handle filter clear
   */
  function handleClearFilter() {
    currentPrefix = '';
    prefixFilter.value = '';
    console.log('Clearing prefix filter');
    loadFiles();
  }
  
  /**
   * Switch view mode
   */
  function switchView(view) {
    if (view === currentView) return;
    
    currentView = view;
    
    if (view === 'table') {
      viewTableBtn.classList.add('active');
      viewGridBtn.classList.remove('active');
      tableView.style.display = 'block';
      gridView.style.display = 'none';
    } else {
      viewGridBtn.classList.add('active');
      viewTableBtn.classList.remove('active');
      gridView.style.display = 'block';
      tableView.style.display = 'none';
    }
    
    console.log('Switched to', view, 'view');
  }
  
  /**
   * Show loading state
   */
  function showLoading() {
    loadingState.style.display = 'block';
    tableView.style.display = 'none';
    gridView.style.display = 'none';
    errorState.style.display = 'none';
  }
  
  /**
   * Hide loading state
   */
  function hideLoading() {
    loadingState.style.display = 'none';
  }
  
  /**
   * Show error state
   */
  function showError(message) {
    hideLoading();
    errorState.innerHTML = `<p class="error">${escapeHtml(message)}</p>`;
    errorState.style.display = 'block';
    tableView.style.display = 'none';
    gridView.style.display = 'none';
  }
  
  /**
   * Show upload status
   */
  function showUploadStatus(message, type) {
    uploadStatus.textContent = message;
    uploadStatus.className = type;
    
    if (type === 'success') {
      setTimeout(() => {
        uploadStatus.textContent = '';
        uploadStatus.className = '';
      }, 5000);
    }
  }
  
  /**
   * Open modal
   */
  function openModal(modal) {
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
  }
  
  /**
   * Close modal
   */
  function closeModal(modal) {
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
  }
  
  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
});

