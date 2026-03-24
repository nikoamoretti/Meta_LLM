import React from 'react';
import Link from 'next/link';

interface Model {
  model_name: string;
  benchmarks: Record<string, number>;
  average_score: number;
}

interface Benchmark {
  name: string;
  source_url: string;
  description: string;
}

interface CodingData {
  category: string;
  total_models: number;
  available_benchmarks: Benchmark[];
  models: Model[];
}

interface Props {
  data: CodingData | null;
  error: string | null;
}

export default function SimpleModelsPage({ data, error }: Props) {
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">⚠️ Error</div>
          <p className="text-gray-600">{error}</p>
          <Link href="/simple-models" className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
            Retry
          </Link>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const sortedModels = [...data.models].sort((a, b) => b.average_score - a.average_score);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Coding AI Model Rankings</h1>
              <p className="text-gray-600">
                Fresh benchmark results from Aider.chat and SWE-Bench
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/" className="text-blue-600 hover:text-blue-800 font-medium">
                ← Home
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="bg-blue-50 border-b">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-8 text-sm">
              <span className="text-blue-700">
                <strong>{data.total_models}</strong> coding models
              </span>
              <span className="text-blue-700">
                Benchmarks: {data.available_benchmarks.map(b => b.name).join(', ')}
              </span>
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                Fresh Data ✅
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rank
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Model
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Average Score
                  </th>
                  {data.available_benchmarks.map(benchmark => (
                    <th key={benchmark.name} className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <div className="flex flex-col">
                        <span>{benchmark.name}</span>
                        {benchmark.source_url && (
                          <a 
                            href={benchmark.source_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-xs text-blue-500 hover:text-blue-700 underline"
                          >
                            Source
                          </a>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sortedModels.map((model, index) => (
                  <tr key={model.model_name} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      #{index + 1}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {model.model_name}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-lg font-bold text-blue-600">
                        {model.average_score.toFixed(1)}%
                      </span>
                    </td>
                    {data.available_benchmarks.map(benchmark => (
                      <td key={benchmark.name} className="px-6 py-4 whitespace-nowrap">
                        {model.benchmarks[benchmark.name] ? (
                          <span className={`inline-flex items-center px-2 py-1 rounded-md text-sm font-medium ${
                            model.benchmarks[benchmark.name] >= 80 ? 'bg-green-100 text-green-800' :
                            model.benchmarks[benchmark.name] >= 60 ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {model.benchmarks[benchmark.name].toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Benchmark Sources */}
        <div className="mt-8 bg-blue-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-4">Benchmark Sources</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.available_benchmarks.map(benchmark => (
              <div key={benchmark.name} className="bg-white rounded-lg p-4 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-gray-900">{benchmark.name}</h4>
                  {benchmark.source_url && (
                    <a 
                      href={benchmark.source_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 text-sm underline"
                    >
                      Visit →
                    </a>
                  )}
                </div>
                <p className="text-sm text-gray-600">{benchmark.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 bg-gray-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">About These Rankings</h3>
          <p className="text-gray-700 mb-4">
            Raw benchmark scores from {data.total_models} coding models across {data.available_benchmarks.length} benchmarks. 
            All data sourced directly from official leaderboards with complete transparency.
          </p>
          <div className="flex space-x-4 text-sm">
            <a href="/api/v3/coding/aider" className="text-blue-600 hover:text-blue-800 underline">
              Aider.chat API
            </a>
            <a href="/api/v3/coding/swe-bench" className="text-blue-600 hover:text-blue-800 underline">
              SWE-Bench API
            </a>
            <a href="/api/v3/coding/benchmarks" className="text-blue-600 hover:text-blue-800 underline">
              Full API
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

export async function getServerSideProps() {
  try {
    // Use the internal container network for server-side calls
    const response = await fetch('http://backend:8000/api/v3/coding/benchmarks?limit=1000');
    
    if (!response.ok) {
      throw new Error(`Failed to fetch models: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    return {
      props: {
        data,
        error: null
      }
    };
  } catch (error) {
    console.error('Server-side fetch error:', error);
    return {
      props: {
        data: null,
        error: error instanceof Error ? error.message : 'Failed to load models'
      }
    };
  }
}