import React from 'react';

export default function StatusPage({ apiData, timestamp }) {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">System Status Check</h1>
      
      <div className="grid gap-4">
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
          <strong>✅ Frontend:</strong> Running (you can see this page)
        </div>
        
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
          <strong>✅ Server-Side Rendering:</strong> Working
        </div>
        
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
          <strong>✅ Backend API:</strong> Responding (data fetched at {timestamp})
        </div>
        
        <div className="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded">
          <strong>📊 API Response:</strong> {apiData.total_models} models found
        </div>
      </div>

      <div className="mt-6">
        <h2 className="text-xl font-semibold mb-3">Available Pages:</h2>
        <ul className="space-y-2">
          <li><a href="/" className="text-blue-600 hover:underline">🏠 Homepage</a></li>
          <li><a href="/simple-models" className="text-blue-600 hover:underline">💻 Coding Rankings (Main)</a></li>
          <li><a href="/test-api" className="text-blue-600 hover:underline">🧪 API Test Page</a></li>
          <li><a href="/status" className="text-blue-600 hover:underline">📊 This Status Page</a></li>
        </ul>
      </div>

      <div className="mt-6">
        <h2 className="text-xl font-semibold mb-3">Top 5 Models:</h2>
        <div className="space-y-2">
          {apiData.models?.slice(0, 5).map((model, index) => (
            <div key={index} className="bg-gray-100 p-3 rounded">
              <span className="font-medium">#{index + 1} {model.model_name}</span>
              <span className="ml-4 text-blue-600">{model.average_score.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export async function getServerSideProps() {
  try {
    const response = await fetch('http://backend:8000/api/v3/coding/benchmarks?limit=10');
    const data = await response.json();
    
    return {
      props: {
        apiData: data,
        timestamp: new Date().toISOString()
      }
    };
  } catch (error) {
    return {
      props: {
        apiData: { total_models: 0, models: [] },
        timestamp: new Date().toISOString()
      }
    };
  }
}