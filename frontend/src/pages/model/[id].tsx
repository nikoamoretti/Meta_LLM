import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

interface ModelDetail {
  model: string;
  overall: number;
  global_rank: number;
  code: number | null;
  hallucination: number | null;
  medical: number | null;
  legal: number | null;
  multilingual: number | null;
  chinese: number | null;
  emotional: number | null;
  instruction: number | null;
  finance: number | null;
  general: number | null;
  benchmarks: Array<{
    name: string;
    benchmark: string;
    metric: string;
    score: number;
    higher_is_better: boolean;
    category: string;
  }>;
  history: Array<any>;
  benchmark_count: number;
}

export default function ModelDetail() {
  const router = useRouter();
  const { id } = router.query;
  const [modelData, setModelData] = useState<ModelDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id && typeof id === 'string') {
      fetchModelDetail(id);
    }
  }, [id]);

  const fetchModelDetail = async (modelName: string) => {
    try {
      const response = await fetch(`http://localhost:8000/models/${encodeURIComponent(modelName)}`);
      const data = await response.json();
      setModelData(data);
    } catch (error) {
      console.error('Error fetching model detail:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatScore = (score: number | null): string => {
    if (score === null) return 'N/A';
    return score < 100 ? score.toFixed(1) : Math.round(score).toLocaleString();
  };

  const getCategoryIcon = (category: string): string => {
    const icons: { [key: string]: string } = {
      general: '🧠',
      code: '💻',
      medical: '🏥',
      legal: '⚖️',
      multilingual: '🌍',
      chinese: '🇨🇳',
      emotional: '💭',
      instruction: '📋',
      finance: '💰',
      hallucination: '🎯'
    };
    return icons[category] || '📊';
  };

  const getRankColor = (rank: number | null): string => {
    if (!rank) return 'text-gray-400';
    if (rank === 1) return 'text-yellow-400';
    if (rank <= 3) return 'text-blue-400';
    if (rank <= 10) return 'text-green-400';
    return 'text-gray-300';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading model details...</div>
      </div>
    );
  }

  if (!modelData) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-white text-xl mb-4">Model not found</div>
          <Link href="/">
            <a className="text-purple-400 hover:text-purple-300">← Back to Leaderboard</a>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <Link href="/">
                <a className="text-purple-400 hover:text-purple-300 mb-4 inline-block">
                  ← Back to Leaderboard
                </a>
              </Link>
              <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-blue-400">
                {modelData.model.toUpperCase()}
              </h1>
              <div className="flex items-center gap-4 mt-2">
                <span className={`text-2xl font-bold ${getRankColor(modelData.global_rank)}`}>
                  #{modelData.global_rank} Global Rank
                </span>
                <span className="text-gray-400">•</span>
                <span className="text-gray-300">{modelData.benchmark_count} Benchmarks</span>
              </div>
            </div>
            
            <div className="text-right">
              <div className="text-3xl font-bold text-green-400">
                {formatScore(modelData.overall)}
              </div>
              <div className="text-gray-400">Overall Score</div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Category Scores */}
          <div className="lg:col-span-2">
            <div className="bg-gray-800 rounded-xl p-6 mb-8">
              <h2 className="text-2xl font-semibold mb-6">Performance by Category</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { key: 'general', label: 'General', score: modelData.general },
                  { key: 'code', label: 'Code', score: modelData.code },
                  { key: 'medical', label: 'Medical', score: modelData.medical },
                  { key: 'legal', label: 'Legal', score: modelData.legal },
                  { key: 'multilingual', label: 'Multilingual', score: modelData.multilingual },
                  { key: 'chinese', label: 'Chinese', score: modelData.chinese },
                  { key: 'emotional', label: 'Emotional', score: modelData.emotional },
                  { key: 'instruction', label: 'Instruction', score: modelData.instruction },
                  { key: 'finance', label: 'Finance', score: modelData.finance },
                  { key: 'hallucination', label: 'Truthfulness', score: modelData.hallucination }
                ].map(({ key, label, score }) => (
                  <div key={key} className="bg-gray-700 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{getCategoryIcon(key)}</span>
                        <span className="font-medium">{label}</span>
                      </div>
                      <span className="text-lg font-bold text-purple-400">
                        {formatScore(score)}
                      </span>
                    </div>
                    {score && (
                      <div className="w-full bg-gray-600 rounded-full h-2">
                        <div 
                          className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full"
                          style={{ width: `${Math.min(score, 100)}%` }}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Benchmark Details */}
            <div className="bg-gray-800 rounded-xl p-6">
              <h2 className="text-2xl font-semibold mb-6">Benchmark Results</h2>
              
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left py-3 px-2 text-gray-400 font-medium">Leaderboard</th>
                      <th className="text-left py-3 px-2 text-gray-400 font-medium">Benchmark</th>
                      <th className="text-left py-3 px-2 text-gray-400 font-medium">Metric</th>
                      <th className="text-left py-3 px-2 text-gray-400 font-medium">Score</th>
                      <th className="text-left py-3 px-2 text-gray-400 font-medium">Category</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modelData.benchmarks.map((benchmark, index) => (
                      <tr key={index} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                        <td className="py-3 px-2 font-medium">{benchmark.name}</td>
                        <td className="py-3 px-2 text-gray-300">{benchmark.benchmark}</td>
                        <td className="py-3 px-2 text-gray-300">{benchmark.metric}</td>
                        <td className="py-3 px-2">
                          <span className="font-bold text-green-400">
                            {formatScore(benchmark.score)}
                          </span>
                        </td>
                        <td className="py-3 px-2">
                          <span className="inline-flex items-center gap-1 bg-gray-700 px-2 py-1 rounded-full text-sm">
                            {getCategoryIcon(benchmark.category)}
                            <span className="capitalize">{benchmark.category}</span>
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Radar Chart Placeholder */}
            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-xl font-semibold mb-4">Performance Radar</h3>
              <div className="aspect-square bg-gray-700 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <div className="text-4xl mb-2">📊</div>
                  <div className="text-gray-400">Radar chart coming soon...</div>
                </div>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-xl font-semibold mb-4">Quick Stats</h3>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-400">Global Rank</span>
                  <span className={`font-bold ${getRankColor(modelData.global_rank)}`}>
                    #{modelData.global_rank}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Overall Score</span>
                  <span className="font-bold text-green-400">{formatScore(modelData.overall)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Benchmarks</span>
                  <span className="font-bold text-blue-400">{modelData.benchmark_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Best Category</span>
                  <span className="font-bold text-purple-400">
                    {Object.entries({
                      general: modelData.general,
                      code: modelData.code,
                      medical: modelData.medical,
                      legal: modelData.legal,
                      multilingual: modelData.multilingual,
                      chinese: modelData.chinese,
                      emotional: modelData.emotional,
                      instruction: modelData.instruction,
                      finance: modelData.finance,
                      hallucination: modelData.hallucination
                    })
                    .filter(([_, score]) => score !== null)
                    .sort(([_, a], [__, b]) => (b as number) - (a as number))[0]?.[0] || 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            {/* Historical Performance */}
            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-xl font-semibold mb-4">Historical Trends</h3>
              <div className="bg-gray-700 rounded-lg p-4 text-center">
                <div className="text-2xl mb-2">📈</div>
                <div className="text-gray-400">History tracking coming soon...</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 