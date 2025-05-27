import { useEffect, useState } from 'react';

export default function Simple() {
  const [status, setStatus] = useState('Starting...');

  useEffect(() => {
    setStatus('Fetching...');
    
    fetch('/api/models')
      .then(res => {
        setStatus(`Response: ${res.status}`);
        return res.json();
      })
      .then(data => {
        setStatus(`Success: ${data.length} models`);
      })
      .catch(err => {
        setStatus(`Error: ${err.message}`);
      });
  }, []);

  return (
    <div style={{ padding: '50px', fontSize: '24px' }}>
      <h1>API Test</h1>
      <p>Status: {status}</p>
    </div>
  );
} 