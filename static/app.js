const form = document.querySelector('#upload-form');
const input = document.querySelector('#candle-file');
const dropzone = document.querySelector('.dropzone');
const fileName = document.querySelector('#file-name');
const demoButton = document.querySelector('#demo-button');
const errorBox = document.querySelector('#error');
const emptyState = document.querySelector('#empty-state');
const dashboard = document.querySelector('#dashboard');
const resultTitle = document.querySelector('#result-title');
const scanTime = document.querySelector('#scan-time');

input.addEventListener('change', () => { fileName.textContent = input.files[0]?.name || 'or browse from your computer'; });
['dragenter', 'dragover'].forEach(eventName => dropzone.addEventListener(eventName, event => { event.preventDefault(); dropzone.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(eventName => dropzone.addEventListener(eventName, event => { event.preventDefault(); dropzone.classList.remove('dragging'); }));
dropzone.addEventListener('drop', event => { input.files = event.dataTransfer.files; fileName.textContent = input.files[0]?.name || 'or browse from your computer'; });

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!input.files[0]) return showError('Choose a JSON or CSV candle file first.');
  const body = new FormData(); body.append('file', input.files[0]);
  await request('/api/analyze-upload', { method: 'POST', body });
});
demoButton.addEventListener('click', () => request('/api/demo'));

async function request(url, options = {}) {
  clearError();
  resultTitle.textContent = 'Scanning candles...';
  try {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The scan could not be completed.');
    render(data);
  } catch (error) { showError(error.message); resultTitle.textContent = 'Waiting for candle data'; }
}

function render(data) {
  emptyState.hidden = true; dashboard.hidden = false;
  resultTitle.textContent = `${data.setup_count} qualifying setup${data.setup_count === 1 ? '' : 's'} found`;
  scanTime.textContent = `${data.candle_count} candles / ${new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}`;
  document.querySelector('#metrics').innerHTML = [
    ['Candles', data.candle_count], ['FVGs', data.fvg_count], ['Setups >= 2', data.setup_count], ['Order blocks', data.order_block_count]
  ].map(([label, value]) => `<div class="metric"><span class="metric-label">${label}</span><span class="metric-value">${value}</span></div>`).join('');
  document.querySelector('#table-caption').textContent = data.alerts.length ? 'Newest signals last' : 'No imbalance found';
  document.querySelector('#alerts-body').innerHTML = data.alerts.slice().reverse().map(alert => `<tr>
    <td><span class="signal">${alert.type.replace('_', ' ')}</span><small>${alert.time}</small></td>
    <td>${Number(alert.bottom).toFixed(2)} - ${Number(alert.top).toFixed(2)}<small>${alert.volume_surge}x volume</small></td>
    <td class="score">${alert.confluence_count}/4</td>
    <td><span class="badge">${alert.confluence.htf_bias}</span></td>
    <td><span class="badge">${alert.confluence.zone}</span></td>
    <td class="check-list">${alert.passed_checks.join('<br>') || 'No checks passed'}</td>
  </tr>`).join('');
}
function showError(message) { errorBox.textContent = message; errorBox.hidden = false; }
function clearError() { errorBox.hidden = true; errorBox.textContent = ''; }
