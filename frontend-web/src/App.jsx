import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';

const STYLES = `
  .vt-root{
    --ink:#1B2A22;
    --paper:#EFE8D8;
    --plate-yellow:#F2B705;
    --oxide:#B23A24;
    --night:#12201C;
    --night-2:#1B2E27;
    --line:#c9bfa2;
    --ok:#3E6B4F;
    min-height:100vh;
    width:100%;
    background:var(--night);
    background-image:
      radial-gradient(circle at 20% 10%, rgba(242,183,5,0.05), transparent 40%),
      radial-gradient(circle at 85% 80%, rgba(242,183,5,0.04), transparent 45%);
    display:flex;
    justify-content:center;
    padding:48px 20px 80px;
    font-family:'Work Sans', sans-serif;
    box-sizing:border-box;
  }
  .vt-root *{ box-sizing:border-box; }
  .vt-stage{ width:100%; max-width:760px; }
  .vt-head{ text-align:center; margin-bottom:28px; }
  .vt-eyebrow{
    font-family:'JetBrains Mono', monospace;
    font-size:11px; letter-spacing:0.28em; text-transform:uppercase;
    color:var(--plate-yellow); opacity:0.85;
  }
  .vt-head h1{
    font-family:'Space Mono', monospace;
    color:var(--paper);
    font-size:clamp(24px, 4vw, 34px);
    margin:8px 0 0; font-weight:700; letter-spacing:-0.01em;
  }
  .vt-head p{ color:#8fa79b; font-size:14px; margin:10px 0 0; }

  .vt-config{
    max-width:760px; margin:0 auto 18px; display:flex; align-items:center; gap:10px;
    font-family:'JetBrains Mono', monospace; font-size:11.5px; color:#6f8479;
  }
  .vt-config input{
    flex:1; background:#0e1a15; border:1px solid #2a3c34; color:#cfe0d7;
    border-radius:4px; padding:8px 10px; font-family:'JetBrains Mono', monospace; font-size:12px;
  }
  .vt-config input:focus{ outline:1px solid var(--plate-yellow); border-color:var(--plate-yellow); }

  .vt-ticket{
    position:relative; background:var(--paper); border-radius:6px;
    box-shadow:0 30px 60px -25px rgba(0,0,0,0.6), 0 2px 0 rgba(255,255,255,0.4) inset;
    color:var(--ink);
  }
  .vt-top{
    display:flex; justify-content:space-between; align-items:flex-start;
    padding:22px 28px 14px; border-bottom:1px dashed var(--line);
  }
  .vt-id{ font-family:'JetBrains Mono', monospace; font-size:11px; letter-spacing:0.08em; color:#6b6350; }
  .vt-id b{ color:var(--ink); }
  .vt-stamp{
    font-family:'Space Mono', monospace; font-size:11px; letter-spacing:0.12em; text-transform:uppercase;
    color:var(--oxide); border:1.5px solid var(--oxide); border-radius:3px; padding:4px 9px;
    transform:rotate(2deg); opacity:0.85;
  }

  .vt-form{ padding:26px 28px 8px; display:grid; grid-template-columns:1fr 1fr; gap:22px 24px; }
  .vt-field{ display:flex; flex-direction:column; gap:6px; }
  .vt-field.full{ grid-column:1 / -1; }
  .vt-field label{
    font-family:'JetBrains Mono', monospace; font-size:10.5px; letter-spacing:0.14em;
    text-transform:uppercase; color:#786f57;
  }
  .vt-field input, .vt-field select{
    font-family:'Work Sans', sans-serif; font-size:15px; color:var(--ink);
    background:transparent; border:none; border-bottom:1.5px dotted #a89f85;
    padding:6px 2px 8px; outline:none; appearance:none;
  }
  .vt-field select{ cursor:pointer; }
  .vt-field input:focus, .vt-field select:focus{ border-bottom:1.5px solid var(--ok); }

  .vt-perf{
    grid-column:1 / -1; display:flex; align-items:center; gap:6px; margin:14px 0 0; padding:0 8px;
  }
  .vt-perf::before, .vt-perf::after{ content:""; flex:1; border-top:1.5px dashed var(--line); }
  .vt-perf span{
    font-family:'JetBrains Mono', monospace; font-size:10px; letter-spacing:0.2em;
    color:#9a9078; text-transform:uppercase; white-space:nowrap;
  }

  .vt-actions{ grid-column:1 / -1; display:flex; justify-content:flex-end; padding:18px 0 26px; }
  .vt-btn{
    font-family:'Space Mono', monospace; font-weight:700; font-size:13.5px; letter-spacing:0.06em;
    text-transform:uppercase; background:var(--ink); color:var(--plate-yellow);
    border:none; border-radius:3px; padding:13px 22px; cursor:pointer;
    transition:transform 0.15s ease, background 0.15s ease;
  }
  .vt-btn:hover:not(:disabled){ background:#0f1913; transform:translateY(-1px); }
  .vt-btn:disabled{ opacity:0.5; cursor:progress; }

  .vt-stub{
    position:relative; background:var(--night-2); color:var(--paper);
    border-radius:0 0 6px 6px; padding:26px 28px 30px;
  }
  .vt-stub::before, .vt-stub::after{
    content:""; position:absolute; top:-11px; width:22px; height:22px;
    background:var(--night); border-radius:50%;
  }
  .vt-stub::before{ left:-11px; }
  .vt-stub::after{ right:-11px; }
  .vt-stub-label{
    font-family:'JetBrains Mono', monospace; font-size:10.5px; letter-spacing:0.2em;
    text-transform:uppercase; color:#8fa79b; margin-bottom:10px;
  }
  .vt-odometer{ display:flex; align-items:baseline; gap:4px; flex-wrap:wrap; min-height:52px; }
  .vt-currency{
    font-family:'Space Mono', monospace; font-size:20px; color:var(--plate-yellow);
    margin-right:6px; align-self:center;
  }
  .vt-digit-wrap{
    overflow:hidden; height:52px; width:30px; background:#0e1a15;
    border-radius:4px; border:1px solid #2a3c34;
  }
  .vt-comma{
    width:14px; background:transparent; border:none; display:flex;
    align-items:flex-end; justify-content:center; height:52px; padding-bottom:8px;
    font-family:'Space Mono', monospace; font-size:22px; color:#7d9488;
  }
  .vt-digit-col{ display:flex; flex-direction:column; transition:transform 1.1s cubic-bezier(.2,.8,.2,1); }
  .vt-digit-col div{
    height:52px; display:flex; align-items:center; justify-content:center;
    font-family:'Space Mono', monospace; font-size:28px; font-weight:700; color:var(--paper);
  }
  .vt-stub-foot{ margin-top:18px; font-size:12.5px; color:#7d9488; line-height:1.6; }
  .vt-ok-dot{ display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--ok); margin-right:6px; }
  .vt-error{
    color:#f2b3a3; font-family:'JetBrains Mono', monospace; font-size:12.5px;
    margin-top:14px; line-height:1.6;
  }

  @media (max-width:600px){
    .vt-form{ grid-template-columns:1fr; }
    .vt-digit-wrap{ width:22px; height:44px; }
    .vt-digit-col div{ height:44px; font-size:22px; }
  }
  @media (prefers-reduced-motion: reduce){
    .vt-digit-col{ transition:none; }
  }
`;

const DIGIT_H = 52;

// Dropdown options extracted from the dataset
const BRANDS = ['AUDI','TOYOTA', 'SUZUKI', 'NISSAN', 'HONDA', 'MITSUBISHI', 'PERODUA', 'MICRO', 'HYUNDAI', 'MAZDA', 'MERCEDES-BENZ', 'TATA', 'KIA', 'DAIHATSU', 'BMW', 'RENAULT'];
const TOWNS = ['Colombo', 'Gampaha', 'Kurunegala', 'Kandy', 'Matara', 'Malabe', 'Galle', 'Kadawatha', 'Negombo', 'Anuradapura', 'Homagama', 'Dehiwala-Mount-Lavinia', 'Kegalle', 'Panadura', 'Kalutara'];
const FUEL_TYPES = ['Petrol', 'Diesel', 'Hybrid', 'Electric'];
const GEARS = ['Automatic', 'Manual'];
const YEARS = Array.from({ length: 35 }, (_, i) => 2024 - i);

function Odometer({ formatted }) {
  const [rolled, setRolled] = useState(false);

  useEffect(() => {
    setRolled(false);
    const t = setTimeout(() => setRolled(true), 30);
    return () => clearTimeout(t);
  }, [formatted]);

  if (!formatted) return null;

  return (
    <div className="vt-odometer">
      <span className="vt-currency">Rs.</span>
      {formatted.split('').map((ch, i) => {
        if (ch === ',') {
          return <div key={i} className="vt-digit-wrap vt-comma">,</div>;
        }
        const digit = parseInt(ch, 10);
        return (
          <div key={i} className="vt-digit-wrap">
            <div
              className="vt-digit-col"
              style={{ transform: `translateY(-${rolled ? digit * DIGIT_H : 0}px)` }}
            >
              {Array.from({ length: 10 }, (_, n) => <div key={n}>{n}</div>)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function App() {
  const [apiBase, setApiBase] = useState('http://127.0.0.1:8000');
  const [formData, setFormData] = useState({
    brand: 'TOYOTA',
    model_name: 'Corolla',
    yom: 2015,
    engine_cc: 1500,
    gear: 'Automatic',
    fuel_type: 'Petrol',
    millage: 80000,
    town: 'Colombo'
  });

  const [prediction, setPrediction] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const ticketNo = useMemo(
    () => 'SL-' + Math.floor(100000 + Math.random() * 900000),
    []
  );

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: ['yom', 'engine_cc', 'millage'].includes(name) ? Number(value) : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      const response = await axios.post(`${apiBase.replace(/\/$/, '')}/predict`, formData);
      // API returns the price in Lakhs (e.g. 42.5 = Rs. 4,250,000) — convert to full rupees
      setPrediction(Math.round(response.data.predicted_price_lkr * 100000));
    } catch (err) {
      setPrediction(null);
      setError('Could not reach the valuation engine. Ensure your FastAPI backend is running.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatted = prediction != null ? prediction.toLocaleString('en-US') : '';

  return (
    <div className="vt-root">
      <style>{STYLES}</style>
      <div className="vt-stage">
        <div className="vt-head">
          <div className="vt-eyebrow">Sri Lankan Car Valuation Engine</div>
          <h1>Vehicle Valuation Ticket</h1>
          <p>Fill in the vehicle details below to get an estimated market price.</p>
        </div>

        <div className="vt-config">
          <label htmlFor="apiBase" style={{ whiteSpace: 'nowrap' }}>API base</label>
          <input
            id="apiBase"
            type="text"
            value={apiBase}
            spellCheck={false}
            onChange={(e) => setApiBase(e.target.value)}
          />
        </div>

        <div className="vt-ticket">
          <div className="vt-top">
            <div className="vt-id">TICKET NO. <b>{ticketNo}</b></div>
            <div className="vt-stamp">Est. valuation</div>
          </div>

          <form className="vt-form" onSubmit={handleSubmit}>
            <div className="vt-field">
              <label htmlFor="brand">Brand</label>
              <select id="brand" name="brand" value={formData.brand} onChange={handleChange} required>
                {BRANDS.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div className="vt-field">
              <label htmlFor="model_name">Model</label>
              <input id="model_name" name="model_name" type="text" value={formData.model_name} onChange={handleChange} placeholder="e.g. Corolla, Civic" required />
            </div>

            <div className="vt-field">
              <label htmlFor="yom">Year of manufacture</label>
              <select id="yom" name="yom" value={formData.yom} onChange={handleChange} required>
                {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
            <div className="vt-field">
              <label htmlFor="engine_cc">Engine (cc)</label>
              <input id="engine_cc" name="engine_cc" type="number" value={formData.engine_cc} onChange={handleChange}  required />
            </div>

            <div className="vt-field">
              <label htmlFor="gear">Transmission</label>
              <select id="gear" name="gear" value={formData.gear} onChange={handleChange} required>
                {GEARS.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
            <div className="vt-field">
              <label htmlFor="fuel_type">Fuel type</label>
              <select id="fuel_type" name="fuel_type" value={formData.fuel_type} onChange={handleChange} required>
                {FUEL_TYPES.map(f => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>

            <div className="vt-field">
              <label htmlFor="millage">Mileage (km)</label>
              <input id="millage" name="millage" type="number" value={formData.millage} onChange={handleChange} min="0" required />
            </div>
            <div className="vt-field">
              <label htmlFor="town">Town</label>
              <select id="town" name="town" value={formData.town} onChange={handleChange} required>
                {TOWNS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div className="vt-perf"><span>Tear along dotted line for estimate</span></div>

            <div className="vt-actions">
              <button className="vt-btn" type="submit" disabled={isLoading}>
                {isLoading ? 'Calculating…' : 'Get valuation'}
              </button>
            </div>
          </form>

          {(prediction != null || error) && (
            <div className="vt-stub">
              <div className="vt-stub-label">Estimated market price</div>
              {prediction != null && <Odometer formatted={formatted} />}
              {prediction != null && (
                <div className="vt-stub-foot">
                  <span className="vt-ok-dot"></span>
                  Based on comparable listings across the model's brand, town profile, and mathematical correlation.
                </div>
              )}
              {error && <div className="vt-error">{error}</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}