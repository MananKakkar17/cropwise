(function () {
  'use strict';

  const cfg = window.CROPWISE || {};
  const i18n = cfg.i18n || {};
  const form = document.querySelector('#recommendation-form');
  const stateSelect = document.querySelector('#weather-state');
  const citySelect = document.querySelector('#weather-city');
  let lastWeather = null;
  let demoStep = 0;

  const demoVisuals = ['🌾', '🌤️', '🧪', '✅'];
  const demoTargets = [null, '#weather-section', '#advisor-form', '#advisor-form'];
  let finalStepAutoCloseTimer = null;

  // ── Location dropdowns ──
  if (stateSelect && citySelect && cfg.locations) {
    stateSelect.addEventListener('change', () => {
      const state = stateSelect.value;
      citySelect.innerHTML = '';
      if (!state) {
        citySelect.disabled = true;
        citySelect.innerHTML = '<option value="">Select state first</option>';
        return;
      }
      citySelect.disabled = false;
      const cities = cfg.locations[state] || [];
      cities.forEach((city) => {
        const opt = document.createElement('option');
        opt.value = city;
        opt.textContent = city;
        citySelect.appendChild(opt);
      });
    });
  }

  // ── Weather fetch ──
  const weatherForm = document.querySelector('#weather-form');
  const weatherResult = document.querySelector('#weather-result');
  const seasonalTip = document.querySelector('#seasonal-tip');

  function renderWeather(w) {
    lastWeather = w;
    weatherResult.hidden = false;
    weatherResult.innerHTML = `
      <div class="weather-header">
        <img src="${w.icon_url}" alt="${w.description}">
        <div>
          <h3>${w.city}${w.state ? ', ' + w.state : ''}</h3>
          <p>${w.description} · Feels like ${w.feels_like}°C</p>
        </div>
      </div>
      <div class="weather-cards">
        <div class="weather-card"><div class="wc-icon">🌡️</div><span class="wc-value">${w.temperature}°C</span><span class="wc-label">${i18n.weatherTemp || 'Temperature'}</span></div>
        <div class="weather-card"><div class="wc-icon">💧</div><span class="wc-value">${w.humidity}%</span><span class="wc-label">${i18n.weatherHumidity || 'Humidity'}</span></div>
        <div class="weather-card"><div class="wc-icon">💨</div><span class="wc-value">${w.wind} km/h</span><span class="wc-label">${i18n.weatherWind || 'Wind'}</span></div>
        <div class="weather-card"><div class="wc-icon">🌧️</div><span class="wc-value">${w.rainfall} mm</span><span class="wc-label">${i18n.weatherRain || 'Rain'}</span></div>
      </div>
      <div class="weather-actions">
        <button type="button" class="button small" id="use-weather">${i18n.weatherApply || 'Use in form'}</button>
      </div>`;

    document.querySelector('#use-weather')?.addEventListener('click', applyWeatherToForm);

    if (w.seasonal_tip || (cfg.seasonalTips && stateSelect?.value)) {
      const tip = w.seasonal_tip || cfg.seasonalTips[stateSelect.value] || '';
      if (tip) {
        seasonalTip.hidden = false;
        seasonalTip.innerHTML = `<b>${i18n.seasonalTip || 'Seasonal tip'}:</b> ${tip}`;
      }
    }
  }

  function applyWeatherToForm() {
    if (!lastWeather || !form) return;
    form.elements.temperature.value = lastWeather.temperature;
    form.elements.humidity.value = lastWeather.humidity;
    if (lastWeather.rainfall > 0) {
      form.elements.rainfall.value = Math.max(lastWeather.rainfall * 30, 80);
    }
    form.querySelector('[name="temperature"]')?.focus();
    document.querySelector('#advisor')?.scrollIntoView({ behavior: 'smooth' });

    // If the farmer is in guided demo step 2 and clicked “Use in form”,
    // auto-advance to the soil entry step.
    if (overlay && !overlay.hidden && demoStep === 1) {
      showDemoStep(2);
    }
  }

  weatherForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const city = citySelect?.value;
    const state = stateSelect?.value;
    if (!city) return;

    weatherResult.hidden = false;
    weatherResult.innerHTML = `<p class="muted">${i18n.weatherLoading || 'Checking weather…'}</p>`;

    try {
      const url = `/api/weather?city=${encodeURIComponent(city)}&state=${encodeURIComponent(state || '')}`;
      const resp = await fetch(url);
      const data = await resp.json();
      if (!data.ok) {
        weatherResult.innerHTML = `<p class="error">${data.message}</p>`;
        return;
      }
      renderWeather(data.weather);
    } catch {
      weatherResult.innerHTML = '<p class="error">Weather service unavailable. Check your internet.</p>';
    }
  });

  // ── Sample data fill ──
  function fillSampleData() {
    const sample = cfg.sampleData || { n: 90, p: 42, k: 43, temperature: 28, humidity: 75, soil_ph: 6.5, rainfall: 180 };
    if (!form) return;
    Object.entries(sample).forEach(([key, val]) => {
      if (form.elements[key]) form.elements[key].value = val;
    });
  }

  // ── Recommendation form ──
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errBox = document.querySelector('#form-error');
    const button = form.querySelector('button[type="submit"]');
    const submitLabel = i18n.advisorSubmit || 'Find my crop plan';
    errBox.textContent = '';
    button.disabled = true;
    button.textContent = i18n.advisorChecking || 'Analyzing…';

    try {
      const payload = Object.fromEntries(new FormData(form));
      const resp = await fetch('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();

      if (!resp.ok) {
        errBox.textContent = Object.values(data.errors || {})[0] || 'Invalid input.';
        return;
      }

      showResults(data);
      document.querySelector('#result-panel')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

      // If guided demo is on/after the soil step and recommendation is shown,
      // close the tour so the farmer can review the result.
      if (overlay && !overlay.hidden && demoStep >= 2) {
        closeDemo();
      }
    } catch {
      errBox.textContent = 'Could not reach advisory service.';
    } finally {
      button.disabled = false;
      button.textContent = submitLabel + ' →';
    }
  });

  function showResults(data) {
    document.querySelector('#result-empty').hidden = true;
    const content = document.querySelector('#result-content');
    content.hidden = false;

    document.querySelector('#crop-name').textContent = data.recommendation.crop;
    const conf = data.recommendation.confidence;
    document.querySelector('#confidence-value').textContent = conf + '%';
    const bar = document.querySelector('#confidence-bar');
    bar.style.width = '0%';
    requestAnimationFrame(() => { bar.style.width = conf + '%'; });

    const quality = data.input_quality || {};
    document.querySelector('#input-quality').textContent = `${quality.label || ''} (${quality.score || 0}%)`;

    document.querySelector('#alternatives').innerHTML = (data.alternatives || [])
      .map((x) => `<span class="chip">${x.crop} <b>${x.confidence}%</b></span>`)
      .join('');

    const maxImp = Math.max(...(data.feature_importance || []).map((x) => x.importance), 1);
    document.querySelector('#importance').innerHTML = (data.feature_importance || [])
      .map((x) => `<div class="importance"><span>${x.feature}</span><i><em style="width:${(x.importance / maxImp) * 100}%"></em></i><b>${x.importance}%</b></div>`)
      .join('');

    const cal = data.crop_calendar || {};
    document.querySelector('#calendar-content').innerHTML = `
      <div class="calendar-row"><span>Sowing:</span> ${cal.sowing || '—'}</div>
      <div class="calendar-row"><span>Harvest:</span> ${cal.harvest || '—'}</div>
      <div class="calendar-row"><span>Tip:</span> ${cal.tip || '—'}</div>`;

    document.querySelector('#fertilizer-text').textContent = data.fertilizer_guidance || '';

    const productMap = {};
    (cfg.products || []).forEach((p) => { productMap[p.id] = p; });

    document.querySelector('#fertilizer-products').innerHTML = (data.fertilizer_products || [])
      .map((fp) => {
        const prod = productMap[fp.product_id];
        if (!prod) return '';
        return `<button type="button" class="product-link-btn add-cart" data-product="${fp.product_id}">${prod.name} · ₹${prod.price}</button>`;
      })
      .join('');

    bindCartButtons();
  }

  // ── Cart ──
  function bindCartButtons() {
    document.querySelectorAll('.add-cart').forEach((btn) => {
      if (btn._bound) return;
      btn._bound = true;
      btn.addEventListener('click', async () => {
        try {
          const resp = await fetch('/cart/add/' + btn.dataset.product, { method: 'POST' });
          const data = await resp.json();
          if (data.ok) {
            const cartLink = document.querySelector('.cart-link');
            if (cartLink) cartLink.textContent = (cartLink.textContent.split('(')[0].trim()) + ' (' + data.count + ')';
            btn.textContent = 'Added ✓';
            btn.style.background = 'var(--green)';
            btn.style.color = '#fff';
          }
        } catch { /* silent */ }
      });
    });
  }
  bindCartButtons();

  // ── Guided demo walkthrough ──
  const overlay = document.querySelector('#demo-overlay');
  const demoTitle = document.querySelector('#demo-step-title');
  const demoText = document.querySelector('#demo-step-text');
  const demoVisual = document.querySelector('#demo-visual');
  const demoIndicator = document.querySelector('#demo-step-indicator');
  const demoNext = document.querySelector('#demo-next');
  const demoSkip = document.querySelector('#demo-skip');
  const demoSample = document.querySelector('#demo-sample');
  const demoStart = document.querySelector('#demo-start');

  function clearHighlights() {
    document.querySelectorAll('.demo-highlight').forEach((el) => el.classList.remove('demo-highlight'));
  }

  function highlightTarget(selector) {
    clearHighlights();
    if (!selector) return;
    const el = document.querySelector(selector);
    if (el) {
      el.classList.add('demo-highlight');
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  function showDemoStep(step) {
    demoStep = step;
    const steps = i18n.demoSteps || [];
    demoIndicator.textContent = `${step + 1} / ${steps.length}`;
    demoText.textContent = steps[step] || '';
    demoVisual.textContent = demoVisuals[step] || '🌾';
    highlightTarget(demoTargets[step]);

    if (step >= steps.length - 1) {
      demoNext.textContent = i18n.demoFinish || 'Start using CropWise';

      // Safety net: if the user can't click the final buttons for any reason,
      // automatically close the guide after a short delay.
      if (finalStepAutoCloseTimer) clearTimeout(finalStepAutoCloseTimer);
      finalStepAutoCloseTimer = setTimeout(() => {
        if (overlay && !overlay.hidden) {
          closeDemo();
          document.querySelector('#advisor')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 1200);
    } else {
      demoNext.textContent = (i18n.demoNext || 'Next') + ' →';
      if (finalStepAutoCloseTimer) {
        clearTimeout(finalStepAutoCloseTimer);
        finalStepAutoCloseTimer = null;
      }
    }
  }

  function openDemo() {
    if (!overlay) return;
    overlay.hidden = false;
    overlay.style.display = 'grid';
    showDemoStep(0);
  }

  function closeDemo() {
    if (!overlay) return;
    overlay.hidden = true;
    overlay.style.display = 'none';
    clearHighlights();
    if (finalStepAutoCloseTimer) {
      clearTimeout(finalStepAutoCloseTimer);
      finalStepAutoCloseTimer = null;
    }
  }

  function demoNextClick() {
    var steps = i18n.demoSteps || [];
    if (demoStep >= steps.length - 1) {
      closeDemo();
      document.querySelector('#advisor')?.scrollIntoView({ behavior: 'smooth' });
    } else {
      showDemoStep(demoStep + 1);
    }
  }

  function demoSampleClick() {
    fillSampleData();
    if (stateSelect) {
      stateSelect.value = 'Maharashtra';
      stateSelect.dispatchEvent(new Event('change'));
      if (citySelect) citySelect.value = 'Pune';
    }
    showDemoStep(2);
  }

  // Expose globally so inline onclick handlers always work
  window._demoClose = closeDemo;
  window._demoNextClick = demoNextClick;
  window._demoSample = demoSampleClick;
  window._demoOpen = openDemo;

  demoStart?.addEventListener('click', openDemo);
  document.querySelector('#demo-button')?.addEventListener('click', openDemo);
  demoNext?.addEventListener('click', demoNextClick);
  demoSkip?.addEventListener('click', closeDemo);
  demoSample?.addEventListener('click', demoSampleClick);

  // Auto-show demo for first-time visitors
  if (!localStorage.getItem('cropwise_demo_seen')) {
    setTimeout(() => {
      openDemo();
      localStorage.setItem('cropwise_demo_seen', '1');
    }, 800);
  }
})();
