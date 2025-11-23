/**
 * Confluence Integration JavaScript
 * Handles all form submissions and tab switching for Confluence operations
 */

document.addEventListener('DOMContentLoaded', function () {
  // Tab switching functionality
  const tabs = document.querySelectorAll('.tab');
  const tabContents = document.querySelectorAll('.tab-content');

  tabs.forEach(tab => {
    tab.addEventListener('click', function () {
      const tabName = this.getAttribute('data-tab');

      // Remove active class from all tabs and contents
      tabs.forEach(t => t.classList.remove('active'));
      tabContents.forEach(tc => tc.classList.remove('active'));

      // Add active class to clicked tab and corresponding content
      this.classList.add('active');
      document.getElementById(tabName).classList.add('active');
    });
  });

  // Load available LLM models for summarization
  loadModels();

  // Form handlers
  setupToMarkdownForm();
  setupFromMarkdownForm();
  setupSummarizeForm();
  setupBackupForm();
  setupStatisticsForm();
});

/**
 * Load available LLM models from Ollama
 */
async function loadModels() {
  try {
    const response = await fetch('/confluence/models');
    if (!response.ok) {
      console.error('Failed to load models:', response.status);
      return;
    }

    const data = await response.json();
    const select = document.getElementById('summarize-model');

    // Clear existing options except default
    while (select.options.length > 1) {
      select.remove(1);
    }

    // Add model options
    data.models.forEach(model => {
      const option = document.createElement('option');
      option.value = model.name;
      option.textContent = `${model.name} (${formatBytes(model.size)})`;
      select.appendChild(option);
    });
  } catch (error) {
    console.error('Error loading models:', error);
  }
}

/**
 * Format bytes to human-readable size
 */
function formatBytes(bytes) {
  if (!bytes) return 'Unknown size';
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  if (bytes === 0) return '0 B';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Show loading indicator
 */
function showLoading(formId, show = true) {
  const form = document.getElementById(formId);
  const loading = form.querySelector('.loading');
  const button = form.querySelector('button[type="submit"]');

  if (show) {
    loading.classList.remove('hidden');
    button.disabled = true;
  } else {
    loading.classList.add('hidden');
    button.disabled = false;
  }
}

/**
 * Show result message
 */
function showResult(resultId, message, isError = false) {
  const resultDiv = document.getElementById(resultId);
  resultDiv.innerHTML = message;
  resultDiv.classList.remove('hidden', 'success', 'error');
  resultDiv.classList.add(isError ? 'error' : 'success');
}

/**
 * Setup: Page to Markdown conversion
 */
function setupToMarkdownForm() {
  const form = document.getElementById('to-markdown-form');
  const resultDiv = document.getElementById('to-markdown-result');

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const pageId = document.getElementById('to-markdown-page-id').value;
    const saveToStorage = document.getElementById('to-markdown-save').checked;

    showLoading('to-markdown-form', true);
    resultDiv.classList.add('hidden');

    try {
      const response = await fetch('/confluence/convert-to-markdown', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          page_id: pageId,
          save_to_storage: saveToStorage,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        showResult(
          'to-markdown-result',
          `<strong>Error ${response.status}:</strong> ${data.detail}`,
          true
        );
        return;
      }

      let message = '<h4>Conversion Successful</h4>';
      if (data.saved_path) {
        message += `<p><strong>Saved to:</strong> ${data.saved_path}</p>`;
      }
      message += '<p><strong>Markdown Content:</strong></p>';
      message += `<div class="markdown-output">${escapeHtml(data.markdown)}</div>`;

      showResult('to-markdown-result', message, false);
    } catch (error) {
      showResult(
        'to-markdown-result',
        `<strong>Network Error:</strong> ${error.message}`,
        true
      );
    } finally {
      showLoading('to-markdown-form', false);
    }
  });
}

/**
 * Setup: Markdown to Page conversion
 */
function setupFromMarkdownForm() {
  const form = document.getElementById('from-markdown-form');
  const resultDiv = document.getElementById('from-markdown-result');

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const spaceKey = document.getElementById('from-markdown-space-key').value;
    const title = document.getElementById('from-markdown-title').value;
    const markdown = document.getElementById('from-markdown-content').value;
    const parentId = document.getElementById('from-markdown-parent').value || null;

    showLoading('from-markdown-form', true);
    resultDiv.classList.add('hidden');

    try {
      const response = await fetch('/confluence/convert-from-markdown', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          space_key: spaceKey,
          title: title,
          markdown: markdown,
          parent_id: parentId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        showResult(
          'from-markdown-result',
          `<strong>Error ${response.status}:</strong> ${data.detail}`,
          true
        );
        return;
      }

      const message = `
        <h4>Page Created/Updated Successfully</h4>
        <p><strong>Page ID:</strong> ${data.page_id}</p>
        <p><strong>Title:</strong> ${data.title}</p>
        <p><strong>URL:</strong> <a href="${data.url}" target="_blank">${data.url}</a></p>
      `;

      showResult('from-markdown-result', message, false);
    } catch (error) {
      showResult(
        'from-markdown-result',
        `<strong>Network Error:</strong> ${error.message}`,
        true
      );
    } finally {
      showLoading('from-markdown-form', false);
    }
  });
}

/**
 * Setup: Page summarization
 */
function setupSummarizeForm() {
  const form = document.getElementById('summarize-form');
  const resultDiv = document.getElementById('summarize-result');

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const pageId = document.getElementById('summarize-page-id').value;
    const model = document.getElementById('summarize-model').value || null;

    showLoading('summarize-form', true);
    resultDiv.classList.add('hidden');

    try {
      const response = await fetch('/confluence/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          page_id: pageId,
          model: model,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        showResult(
          'summarize-result',
          `<strong>Error ${response.status}:</strong> ${data.detail}`,
          true
        );
        return;
      }

      const message = `
        <h4>Summary for: ${escapeHtml(data.page_title)}</h4>
        <div class="markdown-output">${escapeHtml(data.summary)}</div>
      `;

      showResult('summarize-result', message, false);
    } catch (error) {
      showResult(
        'summarize-result',
        `<strong>Network Error:</strong> ${error.message}`,
        true
      );
    } finally {
      showLoading('summarize-form', false);
    }
  });
}

/**
 * Setup: Space backup
 */
function setupBackupForm() {
  const form = document.getElementById('backup-form');
  const resultDiv = document.getElementById('backup-result');

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const spaceKey = document.getElementById('backup-space-key').value;
    const format = document.getElementById('backup-format').value;

    showLoading('backup-form', true);
    resultDiv.classList.add('hidden');

    try {
      const response = await fetch('/confluence/backup-space', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          space_key: spaceKey,
          format: format,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        showResult(
          'backup-result',
          `<strong>Error ${response.status}:</strong> ${data.detail}`,
          true
        );
        return;
      }

      const message = `
        <h4>Backup Completed Successfully</h4>
        <p><strong>Bucket:</strong> ${data.bucket}</p>
        <p><strong>Path:</strong> ${data.path}</p>
        <p><strong>Pages Backed Up:</strong> ${data.page_count}</p>
      `;

      showResult('backup-result', message, false);
    } catch (error) {
      showResult(
        'backup-result',
        `<strong>Network Error:</strong> ${error.message}`,
        true
      );
    } finally {
      showLoading('backup-form', false);
    }
  });
}

/**
 * Setup: Space statistics
 */
function setupStatisticsForm() {
  const form = document.getElementById('statistics-form');
  const resultDiv = document.getElementById('statistics-result');

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const spaceKey = document.getElementById('statistics-space-key').value;

    showLoading('statistics-form', true);
    resultDiv.classList.add('hidden');

    try {
      const response = await fetch('/confluence/statistics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          space_key: spaceKey,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        showResult(
          'statistics-result',
          `<strong>Error ${response.status}:</strong> ${data.detail}`,
          true
        );
        return;
      }

      const message = `
        <h4>Statistics for Space: ${data.space_name} (${data.space_key})</h4>
        <table class="statistics-table">
          <tr>
            <th>Metric</th>
            <th>Value</th>
          </tr>
          <tr>
            <td>Total Pages</td>
            <td>${data.total_pages}</td>
          </tr>
          <tr>
            <td>Total Size</td>
            <td>${formatBytes(data.total_size_bytes)}</td>
          </tr>
          <tr>
            <td>Contributors</td>
            <td>${data.contributors.length} (${data.contributors.join(', ')})</td>
          </tr>
          <tr>
            <td>Last Updated</td>
            <td>${data.last_updated || 'N/A'}</td>
          </tr>
        </table>
      `;

      showResult('statistics-result', message, false);
    } catch (error) {
      showResult(
        'statistics-result',
        `<strong>Network Error:</strong> ${error.message}`,
        true
      );
    } finally {
      showLoading('statistics-form', false);
    }
  });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

