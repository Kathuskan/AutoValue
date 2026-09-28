'use strict';
const $ = (id) => document.getElementById(id);
const form = $('valuation-form');
let metadata, result, loading = false, requestVersion = 0;
const money = new Intl.NumberFormat('en-LK', { maximumFractionDigits: 0 });
const pretty = (text) => text.replaceAll('-', ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
function options(id, values, placeholder) {
  const select = $(id);
  select.replaceChildren(new Option(placeholder, ''));
  values.forEach((value) => select.add(new Option(pretty(value), value)));
}
function clearResult() {
  result = null;
  $('completed-result').hidden = true;
  $('empty-result').hidden = false;
  $('form-error').hidden = true;
  $('copy-status').textContent = '';
  requestVersion += 1;
}
function refreshModels() {
  options('model_name', metadata.brand_models[$('brand').value] || [], 'Choose model');
  refreshEngines();
}
function recordedEngines() {
  const choices = metadata?.engine_options?.[$('brand').value]?.[$('model_name').value] || [];
  return choices;
}
function engineSelection() {
  const choice = $('engine-choice').value;
  const manual = choice === 'manual';
  $('engine_cc').hidden = !manual;
  $('engine-manual-label').hidden = !manual;
  $('engine_cc').readOnly = !manual;
  $('engine_cc').value = manual ? '' : choice;
  $('engine-warning').hidden = !manual;
  $('engine-warning').textContent = manual ? 'Check the engine capacity on your vehicle registration or specifications.' : '';
  clearResult();
}
function manualEngineWarning() {
  if ($('engine-choice').value !== 'manual') return;
  const value = $('engine_cc').value;
  const known = value !== '' && recordedEngines().includes(Number(value));
  $('engine-warning').hidden = known;
  $('engine-warning').textContent = value === ''
    ? 'Enter the capacity from your registration or specifications.'
    : 'Please confirm this engine capacity matches your car’s registration or specifications.';
}
function refreshEngines() {
  const active = Boolean(metadata?.metrics.use_engine);
  const ready = active && $('brand').value && $('model_name').value;
  $('engine-field').hidden = !active;
  $('engine-choice').disabled = !ready;
  $('engine-choice').required = Boolean(ready);
  $('engine_cc').disabled = !ready;
  $('engine_cc').required = Boolean(ready);
  $('engine_cc').value = '';
  $('engine_cc').hidden = true;
  $('engine-manual-label').hidden = true;
  $('engine-warning').hidden = true;
  $('engine-choice').replaceChildren(new Option(ready ? 'Choose engine capacity' : 'Choose brand and model first', ''));
  if (!ready) { $('engine-help').textContent = 'Choose brand and model first.'; return; }
  const values = recordedEngines();
  values.forEach(value => $('engine-choice').add(new Option(`${value.toLocaleString('en-LK')} cc`, String(value))));
  $('engine-choice').add(new Option('My capacity is not listed — enter manually', 'manual'));
  $('engine-help').textContent = values.length === 1
    ? 'Suggested capacity. Check that it matches your car.'
    : values.length > 1 ? 'Choose your car’s engine capacity, or enter another value.'
    : 'Enter the engine capacity shown on your vehicle registration.';
  $('engine-choice').value = values.length === 1 ? String(values[0]) : values.length === 0 ? 'manual' : '';
  engineSelection();
}
async function initialize() {
  $('load-status').textContent = 'Loading vehicle options…';
  $('load-status').classList.remove('failed');
  $('retry').hidden = true;
  try {
    const response = await fetch('/metadata', { signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error('Model unavailable');
    metadata = await response.json();
    options('brand', Object.keys(metadata.brand_models).sort(), 'Choose manufacturer');
    options('gear', metadata.categories.Gear.filter(value => ['AUTOMATIC', 'MANUAL'].includes(value)), 'Choose transmission');
    options('fuel_type', metadata.categories['Fuel Type'], 'Choose fuel type');
    options('condition', metadata.categories.Condition, 'Choose condition');
    $('yom').max = metadata.metrics.reference_year;
    for (const [id, active] of [['millage', metadata.metrics.use_mileage]]) {
      $(id).disabled = !active;
      $(id).required = active;
      $(id).closest('label').hidden = !active;
    }
    refreshEngines();
    $('fields').disabled = false;
    $('example').disabled = false;
    loadExample();
  } catch (error) {
    $('load-status').textContent = 'Vehicle options are unavailable right now. Please try again.';
    $('load-status').classList.add('failed');
    $('retry').hidden = false;
  }
}
$('retry').addEventListener('click', initialize);
$('brand').addEventListener('change', refreshModels);
$('model_name').addEventListener('change', refreshEngines);
$('engine-choice').addEventListener('change', engineSelection);
$('engine_cc').addEventListener('input', manualEngineWarning);
form.addEventListener('input', clearResult);
form.addEventListener('change', clearResult);
function loadExample() {
  const sample = metadata.example;
  $('brand').value = sample.brand; refreshModels();
  Object.entries(sample).forEach(([key, value]) => { $(key).value = value; });
  refreshEngines();
  if (metadata.metrics.use_engine) {
    $('engine-choice').value = recordedEngines().includes(sample.engine_cc) ? String(sample.engine_cc) : 'manual';
    engineSelection();
    $('engine_cc').value = sample.engine_cc;
  }
  clearResult();
  $('load-status').textContent = `Example loaded: ${pretty(sample.brand)} ${sample.model_name}. You can change the details before estimating.`;
}
$('example').addEventListener('click', loadExample);
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (loading || !form.reportValidity()) return;
  clearResult();
  loading = true;
  const version = requestVersion;
  const payload = Object.fromEntries(new FormData(form));
  ['yom', 'engine_cc', 'millage'].forEach((key) => { if (key in payload) payload[key] = Number(payload[key]); });
  $('fields').disabled = true;
  $('example').disabled = true;
  $('submit').textContent = 'Calculating estimate…';
  $('valuation-form').setAttribute('aria-busy', 'true');
  try {
    const response = await fetch('/predict', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal: AbortSignal.timeout(30000) });
    const data = await response.json();
    if (!response.ok) {
      const detail = typeof data.detail === 'string' ? data.detail : 'Please check the vehicle details and try again.';
      throw new Error(detail);
    }
    if (version !== requestVersion) return;
    if (data.currency !== 'LKR' || !Number.isFinite(data.predicted_price_lkr)) throw new Error('We could not calculate an estimate. Please try again.');
    result = data;
    $('price').textContent = 'Rs. ' + money.format(data.predicted_price_lkr);
    $('price-lakhs').textContent = data.predicted_price_lakhs.toFixed(2) + ' lakhs';
    $('vehicle-summary').textContent = `${pretty(payload.brand)} ${payload.model_name} · ${payload.yom}`;
    $('warnings').replaceChildren();
    if (data.warnings?.length) {
      const p = document.createElement('p');
      p.textContent = 'Double-check your vehicle details. This estimate may be less reliable for this car.';
      $('warnings').append(p);
    }
    $('warnings').hidden = !data.warnings?.length;
    $('empty-result').hidden = true;
    $('completed-result').hidden = false;
    if (window.matchMedia('(max-width: 650px)').matches) $('completed-result').scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
  } catch (error) {
    $('form-error').textContent = error.name === 'TimeoutError' ? 'The request took too long. Please try again.' : error instanceof TypeError ? 'Unable to connect. Check that the application is still running and try again.' : error.message;
    $('form-error').hidden = false;
  } finally {
    loading = false;
    $('fields').disabled = false;
    $('example').disabled = false;
    $('submit').innerHTML = 'Estimate asking price <span aria-hidden="true">→</span>';
    form.removeAttribute('aria-busy');
  }
});
$('copy-result').addEventListener('click', async () => {
  if (!result) return;
  const text = `AutoValue LK\n${$('vehicle-summary').textContent}\nEstimated asking price: Rs. ${money.format(result.predicted_price_lkr)} (${result.predicted_price_lakhs.toFixed(2)} lakhs).\nAn indicative estimate, not a guaranteed sale price.${result.warnings?.length ? '\nDouble-check your vehicle details; this estimate may be less reliable for this car.' : ''}`;
  try { await navigator.clipboard.writeText(text); $('copy-status').textContent = 'Copied'; }
  catch { $('copy-status').textContent = 'Copy unavailable. Select the price to copy it.'; }
});
initialize();
