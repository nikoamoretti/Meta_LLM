import { useEffect, useState } from 'react';

export default function Debug() {
  const [status, setStatus] = useState('Starting...');
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<any>(null);

  useEffect(() => {
    setStatus('Fetching...');
    
    fetch('/api/models')
      .then(res => {
        setStatus(`Response: ${res.status} ${res.statusText}`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return res.json();
      })
      .then(data => {
        setStatus(`Success: ${data.length} models`);
        setData(data.slice(0, 3)); // First 3 models
      })
      .catch(err => {
        setStatus(`Error: ${err.message}`);
        setError(err);
      });
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Debug Page</h1>
      <p><strong>Status:</strong> {status}</p>
      
      {error && (
        <div style={{ background: '#ffeeee', padding: '10px', margin: '10px 0' }}>
          <strong>Error:</strong> {error.toString()}
        </div>
      )}
      
      {data && (
        <div style={{ background: '#eeffee', padding: '10px', margin: '10px 0' }}>
          <strong>Sample Data:</strong>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
    </div>
  );
} 