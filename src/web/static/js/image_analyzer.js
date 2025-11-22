document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('image-analyzer-form');
  const resultDiv = document.getElementById('result');
  const historyDiv = document.getElementById('history');

  // Use the nginx proxy path to access the API
  // Note: API routes are at /api/llm/analyze-image (no /v1)
  const API_BASE_URL = '/api';

  console.log('=== IMAGE ANALYZER DEBUG INFO ===');
  console.log('Current page URL:', window.location.href);
  console.log('API Base URL:', API_BASE_URL);
  console.log('Full history URL:', `${API_BASE_URL}/llm/analyze-image`);
  console.log('================================');

  async function fetchHistory() {
    const url = `${API_BASE_URL}/llm/analyze-image`;
    console.log('\n>>> FETCHING HISTORY <<<');
    console.log('Attempting to fetch from:', url);
    console.log('Full URL:', new URL(url, window.location.origin).href);
    
    try {
      const resp = await fetch(url);
      console.log('✓ Fetch completed');
      console.log('Response status:', resp.status, resp.statusText);
      console.log('Response URL:', resp.url);
      console.log('Response headers:', Object.fromEntries(resp.headers.entries()));
      
      if (!resp.ok) {
        console.error('❌ History fetch failed with status:', resp.status);
        const text = await resp.text();
        console.error('Response body (first 500 chars):', text.substring(0, 500));
        console.error('Full response body:', text);
        historyDiv.innerHTML = `<h3>Analysis History</h3>
          <p class="error">
            <strong>Failed to load history (${resp.status})</strong><br>
            URL tried: ${url}<br>
            Status: ${resp.statusText}<br>
            Check console for full details.
          </p>`;
        return;
      }
      
      const contentType = resp.headers.get('content-type');
      console.log('Content-Type:', contentType);
      
      if (!contentType || !contentType.includes('application/json')) {
        const text = await resp.text();
        console.error('❌ Expected JSON but got:', contentType);
        console.error('Response body:', text.substring(0, 500));
        historyDiv.innerHTML = `<h3>Analysis History</h3>
          <p class="error">
            Server returned non-JSON response<br>
            Content-Type: ${contentType}<br>
            Check console for details.
          </p>`;
        return;
      }
      
      const data = await resp.json();
      console.log('✓ Successfully parsed JSON response');
      console.log('Data:', data);
      
      historyDiv.innerHTML = `<h3>Analysis History</h3>` +
        (data.analyses && data.analyses.length ?
        '<ul>' + data.analyses.map(a => `<li><b>${a.filename}</b>: ${a.llm_description || 'No description'}</li>`).join('') + '</ul>'
        : '<p>No analyses yet.</p>');
    } catch (err) {
      console.error('❌ History fetch error:', err);
      console.error('Error name:', err.name);
      console.error('Error message:', err.message);
      console.error('Error stack:', err.stack);
      historyDiv.innerHTML = `<h3>Analysis History</h3>
        <p class="error">
          Network error: ${err.message}<br>
          Check console for full details.
        </p>`;
    }
  }

  if (form) {
    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      const formData = new FormData(form);
      const url = `${API_BASE_URL}/llm/analyze-image`;
      
      console.log('\n>>> SUBMITTING IMAGE ANALYSIS <<<');
      console.log('POST URL:', url);
      console.log('Full URL:', new URL(url, window.location.origin).href);
      console.log('Form data entries:');
      for (let pair of formData.entries()) {
        if (pair[0] === 'file') {
          console.log(`  ${pair[0]}:`, pair[1].name, `(${pair[1].size} bytes, ${pair[1].type})`);
        } else {
          console.log(`  ${pair[0]}:`, pair[1]);
        }
      }
      
      resultDiv.innerHTML = '<p class="loading">Analyzing image... This may take 10-30 seconds depending on image size.</p>';
      
      try {
        const resp = await fetch(url, {
          method: 'POST',
          body: formData,
        });
        
        console.log('✓ POST completed');
        console.log('Response status:', resp.status, resp.statusText);
        console.log('Response URL:', resp.url);
        console.log('Response headers:', Object.fromEntries(resp.headers.entries()));
        
        const contentType = resp.headers.get('content-type');
        console.log('Content-Type:', contentType);
        
        if (!contentType || !contentType.includes('application/json')) {
          const text = await resp.text();
          console.error('❌ Expected JSON but got:', contentType);
          console.error('Response body (first 500 chars):', text.substring(0, 500));
          console.error('Full response body:', text);
          resultDiv.innerHTML = `<p class="error">
            <strong>Server returned non-JSON response (${resp.status})</strong><br>
            URL: ${url}<br>
            Status: ${resp.statusText}<br>
            Content-Type: ${contentType}<br>
            Check console for full details.
          </p>`;
          return;
        }
        
        if (!resp.ok) {
          const err = await resp.json();
          console.error('❌ Analysis failed:', err);
          console.error('Error details:', JSON.stringify(err, null, 2));
          resultDiv.innerHTML = `<p class="error">
            <strong>Error ${resp.status}: ${err.detail || resp.statusText}</strong><br>
            URL: ${url}<br>
            ${err.detail ? `Details: ${err.detail}` : ''}
          </p>`;
          return;
        }
        
        const data = await resp.json();
        console.log('✓ Successfully analyzed image');
        console.log('Analysis result:', JSON.stringify(data, null, 2));
        
        resultDiv.innerHTML = `
          <div class="result-success">
            <h4>Analysis Result for: ${data.filename}</h4>
            <p><strong>Model:</strong> ${data.model_used}</p>
            <p><strong>Description:</strong></p>
            <pre>${data.llm_description || 'No description generated'}</pre>
            <p><strong>Size:</strong> ${(data.metadata.size_bytes / 1024).toFixed(2)} KB</p>
          </div>
        `;
        fetchHistory();
      } catch (err) {
        console.error('❌ Analysis error:', err);
        console.error('Error name:', err.name);
        console.error('Error message:', err.message);
        console.error('Error stack:', err.stack);
        resultDiv.innerHTML = `<p class="error">
          <strong>Network error: ${err.message}</strong><br>
          URL tried: ${url}<br>
          Check console for full details.
        </p>`;
      }
    });
  }
  
  // Initial history load
  fetchHistory();
});
