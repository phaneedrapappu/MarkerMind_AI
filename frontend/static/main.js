/* MarketMind AI – Client-side JS */

/**
 * Trigger a full agent pipeline run via the REST API.
 * Shows visual feedback while the pipeline is running.
 */
function triggerPipeline() {
  const badge = document.getElementById('pipeline-status');
  badge.textContent = 'Starting…';
  badge.className = 'badge bg-warning align-self-center';

  fetch('/api/run', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'started') {
        badge.textContent = 'Running';
        badge.className = 'badge bg-info align-self-center running';
        pollPipelineStatus();
      } else if (data.status === 'already_running') {
        badge.textContent = 'Already Running';
        badge.className = 'badge bg-warning align-self-center running';
        pollPipelineStatus();
      }
    })
    .catch(() => {
      badge.textContent = 'Error';
      badge.className = 'badge bg-danger align-self-center';
    });
}

/**
 * Poll the server every 3 seconds until the pipeline finishes.
 */
function pollPipelineStatus() {
  const badge = document.getElementById('pipeline-status');
  const interval = setInterval(() => {
    fetch('/api/pipeline/status')
      .then(r => r.json())
      .then(data => {
        if (!data.running) {
          clearInterval(interval);
          badge.textContent = 'Done ✓';
          badge.className = 'badge bg-success align-self-center';
          setTimeout(() => {
            badge.textContent = 'Idle';
            badge.className = 'badge bg-secondary align-self-center';
            location.reload();
          }, 2500);
        }
      });
  }, 3000);
}

// Highlight active nav link
document.addEventListener('DOMContentLoaded', () => {
  const links = document.querySelectorAll('.nav-link');
  links.forEach(link => {
    if (link.href === location.href) link.classList.add('active');
  });
});
