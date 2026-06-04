// Main page interactions for AgriIntel
const toastElement = document.getElementById('toast');
const themeToggle = document.getElementById('themeToggle');
const body = document.body;
const schemeGrid = document.getElementById('schemeGrid');
const schemeSearch = document.getElementById('schemeSearch');
const chatWindow = document.getElementById('chatWindow');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const apiBase = '/api';
const defaultMetrics = [3520, 18740, 620, 48];
let loadedSchemes = [];

const initTheme = () => {
  const savedTheme = localStorage.getItem('agriTheme');
  if (savedTheme === 'light') {
    body.classList.add('theme-light');
    themeToggle.textContent = '☀️';
  } else {
    body.classList.remove('theme-light');
    themeToggle.textContent = '🌙';
  }
};

const toggleTheme = () => {
  const isLight = body.classList.toggle('theme-light');
  localStorage.setItem('agriTheme', isLight ? 'light' : 'dark');
  themeToggle.textContent = isLight ? '☀️' : '🌙';
  showToast(isLight ? 'Light mode enabled' : 'Dark mode enabled');
};

const showToast = (message) => {
  toastElement.textContent = message;
  toastElement.classList.add('show');
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => {
    toastElement.classList.remove('show');
  }, 3000);
};

const animateCounters = () => {
  const counters = document.querySelectorAll('.stat-value');
  counters.forEach((counter) => {
    const target = parseInt(counter.dataset.target, 10);
    const duration = 1800;
    let start = 0;
    const stepTime = Math.max(Math.floor(duration / target), 12);
    const update = () => {
      start += Math.ceil(target / (duration / stepTime));
      if (start > target) start = target;
      counter.textContent = start.toLocaleString();
      if (start < target) {
        window.requestAnimationFrame(update);
      }
    };
    update();
  });
};

const revealOnScroll = () => {
  const elements = document.querySelectorAll('.fade-in-up, .fade-in-down, .slide-up');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.style.animationPlayState = 'running';
      }
    });
  }, { threshold: 0.12 });
  elements.forEach((el) => {
    el.style.animationPlayState = 'paused';
    observer.observe(el);
  });
};

const updateMetricCards = (values) => {
  const counters = document.querySelectorAll('.stat-value');
  counters.forEach((counter, index) => {
    counter.dataset.target = values[index];
    counter.textContent = '0';
  });
  animateCounters();
};

const renderSchemes = (schemes) => {
  if (!schemeGrid) return;
  loadedSchemes = schemes;
  schemeGrid.innerHTML = schemes.map((scheme) => `
    <article class="scheme-card glass-card">
      <div class="scheme-card-header">
        <h4>${scheme.name}</h4>
        <span class="scheme-badge">${scheme.status}</span>
      </div>
      <p>${scheme.description}</p>
    </article>
  `).join('');
};

const filterSchemes = () => {
  if (!schemeSearch) return;
  const query = schemeSearch.value.trim().toLowerCase();
  const filtered = loadedSchemes.filter((scheme) =>
    scheme.name.toLowerCase().includes(query) || scheme.status.toLowerCase().includes(query)
  );
  renderSchemes(filtered);
};

const addChatMessage = (message, author) => {
  if (!chatWindow) return;
  const bubble = document.createElement('div');
  bubble.className = `chat-message ${author}`;
  bubble.innerHTML = `<p>${message}</p>`;
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return bubble;
};

const fetchBackendMetrics = async () => {
  try {
    const response = await fetch(`${apiBase}/insights`);
    if (!response.ok) throw new Error('Backend unavailable');
    const result = await response.json();
    const metricValues = [
      result.metrics.farmersSupported,
      result.metrics.marketReports,
      result.metrics.governmentSchemes,
      result.metrics.cropCategories,
    ];
    updateMetricCards(metricValues);
    showToast('Backend connected. Metrics loaded.');
  } catch (error) {
    updateMetricCards(defaultMetrics);
    showToast('Backend unavailable. Using default metrics.');
  }
};

const fetchSchemes = async () => {
  if (!schemeGrid) return;
  try {
    const response = await fetch(`${apiBase}/schemes`);
    if (!response.ok) throw new Error('Failed to load schemes');
    const result = await response.json();
    renderSchemes(result.schemes);
    showToast('Schemes loaded from backend.');
  } catch (error) {
    renderSchemes([
      { name: 'Backend offline', status: 'Unavailable', description: 'Unable to load scheme data from the server.' },
    ]);
    showToast('Could not fetch schemes. Check server status.');
  }
};

const initSchemeSearch = () => {
  if (!schemeSearch) return;
  schemeSearch.addEventListener('input', filterSchemes);
};

const initChat = () => {
  if (!chatForm || !chatInput) return;
  chatForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const question = chatInput.value.trim();
    if (!question) return;
    addChatMessage(question, 'user');
    chatInput.value = '';
    const loader = addChatMessage('Thinking...', 'bot');

    try {
      const response = await fetch(`${apiBase}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: question }),
      });
      const result = await response.json();
      loader.textContent = '';
      loader.innerHTML = `<p>${result.reply || 'No reply received.'}</p>`;
    } catch (error) {
      loader.textContent = '';
      loader.innerHTML = `<p>Backend unavailable. Please start the server.</p>`;
      showToast('Chat service unavailable.');
    }
  });
};

const init = () => {
  initTheme();
  themeToggle.addEventListener('click', toggleTheme);
  revealOnScroll();
  fetchBackendMetrics();
  fetchSchemes();
  initSchemeSearch();
  initChat();
};

window.addEventListener('DOMContentLoaded', init);
