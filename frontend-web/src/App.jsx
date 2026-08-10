import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [formData, setFormData] = useState({
    brand: 'TOYOTA',
    model_name: 'Corolla',
    yom: 2015,
    engine_cc: 1500,
    gear: 'Automatic',
    fuel_type: 'Petrol',
    millage: 80000,
    town: 'Colombo',
    condition: 'USED'
  });
  
  const [prediction, setPrediction] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: name === 'yom' || name === 'engine_cc' || name === 'millage' ? Number(value) : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    
    try {
      const response = await axios.post('http://127.0.0.1:8000/predict', formData);
      setPrediction(response.data.predicted_price_lkr);
    } catch (err) {
      setError('Connection Error. Ensure your FastAPI backend is running.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '600px', margin: '40px auto', fontFamily: 'sans-serif' }}>
      <h1 style={{ textAlign: 'center' }}>Car Valuation Engine</h1>
      
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <label>
          Brand: <input type="text" name="brand" value={formData.brand} onChange={handleChange} style={inputStyle} />
        </label>
        <label>
          Model: <input type="text" name="model_name" value={formData.model_name} onChange={handleChange} style={inputStyle} />
        </label>
        <label>
          Year of Manufacture: <input type="number" name="yom" value={formData.yom} onChange={handleChange} style={inputStyle} />
        </label>
        <label>
          Engine (cc): <input type="number" name="engine_cc" value={formData.engine_cc} onChange={handleChange} style={inputStyle} />
        </label>
        <label>
          Gear (Automatic/Manual): <input type="text" name="gear" value={formData.gear} onChange={handleChange} style={inputStyle} />
        </label>
        <label>
          Fuel Type: <input type="text" name="fuel_type" value={formData.fuel_type} onChange={handleChange} style={inputStyle} />
        </label>
        <label>
          Mileage (KM): <input type="number" name="millage" value={formData.millage} onChange={handleChange} style={inputStyle} />
        </label>
        <label>
          Town: <input type="text" name="town" value={formData.town} onChange={handleChange} style={inputStyle} />
        </label>
        <label>
          Condition (USED/Brand New): <input type="text" name="condition" value={formData.condition} onChange={handleChange} style={inputStyle} />
        </label>

        <button type="submit" disabled={isLoading} style={{ padding: '10px', fontSize: '16px', cursor: 'pointer' }}>
          {isLoading ? 'Predicting...' : 'Predict Price'}
        </button>
      </form>

      {error && <p style={{ color: 'red', textAlign: 'center' }}>{error}</p>}
      
      {prediction && (
        <h2 style={{ textAlign: 'center', color: 'green', marginTop: '30px' }}>
          Estimated Price: {prediction} LKR (Lakhs)
        </h2>
      )}
    </div>
  );
}

const inputStyle = { width: '100%', padding: '8px', marginTop: '5px' };

export default App;