import React, { useState, useEffect } from 'react';
import Link from 'next/link';

interface ModelScore {
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
  benchmark_count: number;
  code_benchmarks?: { [key: string]: number };
  medical_benchmarks?: { [key: string]: number };
  legal_benchmarks?: { [key: string]: number };
}

interface CategoryInfo {
  name: string;
  icon: string;
  description: string;
  benchmarks: string[];
  sources: string[];
  methodology: string;
  scoreKey: keyof ModelScore;
}

const categories: CategoryInfo[] = [
  {
    name: 'Overall',
    icon: '🏆',
    description: 'Comprehensive ranking across all evaluation categories',
    benchmarks: ['Global Composite Score'],
    sources: ['Meta-Leaderboard Aggregator'],
    methodology: 'Weighted average of all category scores, normalized across all benchmarks',
    scoreKey: 'overall'
  },
  {
    name: 'General',
    icon: '🧠',
    description: 'General reasoning, knowledge, and language understanding',
    benchmarks: ['MMLU', 'ChatBot Arena', 'Stanford HELM', 'OpenRouter Usage', 'Vellum AI'],
    sources: ['HuggingFace', 'LMSYS', 'Stanford', 'OpenRouter', 'Vellum AI'],
    methodology: 'Academic knowledge (MMLU), human preference (Arena), holistic evaluation (HELM), real usage (OpenRouter), and advanced reasoning (Vellum)',
    scoreKey: 'general'
  },
  {
    name: 'Code',
    icon: '💻',
    description: 'Programming and software development capabilities',
    benchmarks: ['HumanEval', 'MBPP (Mostly Basic Python Problems)', 'APPS (Automated Programming Progress Standard)'],
    sources: ['BigCode', 'Scale AI', 'Code Domain Benchmarks'],
    methodology: 'Code generation accuracy across multiple programming benchmarks: HumanEval (Python function synthesis), MBPP (basic programming), and APPS (competitive programming)',
    scoreKey: 'code'
  },
  {
    name: 'Medical',
    icon: '🏥',
    description: 'Medical knowledge and healthcare reasoning',
    benchmarks: ['MedQA-USMLE'],
    sources: ['Open Medical LLM Leaderboard'],
    methodology: 'Medical licensing exam questions (USMLE) testing clinical knowledge and diagnostic reasoning',
    scoreKey: 'medical'
  },
  {
    name: 'Legal',
    icon: '⚖️',
    description: 'Legal reasoning and jurisprudence understanding',
    benchmarks: ['LegalBench-Average'],
    sources: ['Stanford LegalBench'],
    methodology: 'Comprehensive legal reasoning tasks covering contract law, constitutional law, and legal analysis',
    scoreKey: 'legal'
  },
  {
    name: 'Multilingual',
    icon: '🌍',
    description: 'Cross-language understanding and reasoning',
    benchmarks: ['Multilingual-Average (29 languages)'],
    sources: ['Open Multilingual LLM Leaderboard'],
    methodology: 'Evaluation across 29 languages testing cross-lingual transfer and multilingual reasoning capabilities',
    scoreKey: 'multilingual'
  },
  {
    name: 'Chinese',
    icon: '🇨🇳',
    description: 'Chinese language understanding and cultural knowledge',
    benchmarks: ['C-Eval-Average'],
    sources: ['C-Eval Leaderboard'],
    methodology: 'Comprehensive Chinese evaluation covering language, culture, and domain-specific knowledge',
    scoreKey: 'chinese'
  },
  {
    name: 'Emotional Intelligence',
    icon: '💭',
    description: 'Emotional understanding and social reasoning',
    benchmarks: ['EQ-Bench-v2'],
    sources: ['EQ-Bench'],
    methodology: 'Emotional intelligence evaluation testing understanding of emotions, social cues, and interpersonal dynamics',
    scoreKey: 'emotional'
  },
  {
    name: 'Instruction Following',
    icon: '📋',
    description: 'Ability to follow complex instructions and user intent',
    benchmarks: ['AlpacaEval 2.0'],
    sources: ['AlpacaEval'],
    methodology: 'Instruction-following evaluation using GPT-4 as judge to assess response quality and user intent alignment',
    scoreKey: 'instruction'
  },
  {
    name: 'Finance',
    icon: '💰',
    description: 'Financial reasoning and economic analysis',
    benchmarks: ['FinQA'],
    sources: ['Finance LLM Leaderboard'],
    methodology: 'Financial question answering testing numerical reasoning, market analysis, and economic understanding',
    scoreKey: 'finance'
  },
  {
    name: 'Truthfulness',
    icon: '🎯',
    description: 'Factual accuracy and hallucination resistance',
    benchmarks: ['Vectara Hallucination Evaluation'],
    sources: ['Vectara'],
    methodology: 'Hallucination detection measuring accuracy vs. fabrication in factual question answering',
    scoreKey: 'hallucination'
  }
];

export default function Home() {
  const [models, setModels] = useState<ModelScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('Overall');

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/models');
      const data = await response.json();
      setModels(data);
    } catch (error) {
      console.error('Error fetching models:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatScore = (score: number | null): string => {
    if (score === null || score === undefined) return '-';
    return score < 100 ? score.toFixed(1) : Math.round(score).toLocaleString();
  };

  const getRankMedal = (rank: number): string => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return rank.toString();
  };

  const getActiveCategory = (): CategoryInfo => {
    return categories.find(cat => cat.name === activeTab) || categories[0];
  };

  const getSortedModels = (): ModelScore[] => {
    const activeCategory = getActiveCategory();
    
    if (activeCategory.name === 'Overall') {
      return [...models].sort((a, b) => b.overall - a.overall);
    } else {
      return [...models]
        .filter(model => model[activeCategory.scoreKey] !== null && model[activeCategory.scoreKey] !== undefined)
        .sort((a, b) => {
          const aScore = a[activeCategory.scoreKey] as number;
          const bScore = b[activeCategory.scoreKey] as number;
          return bScore - aScore;
        });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading leaderboard...</div>
      </div>
    );
  }

  const activeCategory = getActiveCategory();
  const sortedModels = getSortedModels();

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="text-center py-12">
        <h1 className="text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-blue-400 mb-4">
          Meta-Leaderboard
        </h1>
        <p className="text-xl text-gray-300 mb-6">Advanced Language Model Benchmarks</p>
        <div className="inline-block bg-gray-800 px-4 py-2 rounded-full">
          <span className="text-gray-300">Updated: {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6">
        {/* Category Tabs */}
        <div className="bg-gray-800 rounded-xl p-2 mb-8">
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <button
                key={category.name}
                onClick={() => setActiveTab(category.name)}
                className={`flex items-center gap-2 px-4 py-3 rounded-lg transition-all ${
                  activeTab === category.name
                    ? 'bg-purple-600 text-white shadow-lg'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                <span className="text-lg">{category.icon}</span>
                <span className="font-medium">{category.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Category Information */}
        <div className="bg-gray-800 rounded-xl p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-3xl">{activeCategory.icon}</span>
            <h2 className="text-2xl font-bold">{activeCategory.name}</h2>
          </div>
          
          <p className="text-gray-300 mb-6">{activeCategory.description}</p>
          
          <div className="grid md:grid-cols-3 gap-6">
            <div>
              <h3 className="text-lg font-semibold text-purple-400 mb-3">Benchmarks</h3>
              <ul className="space-y-1">
                {activeCategory.benchmarks.map((benchmark, index) => (
                  <li key={index} className="text-gray-300">• {benchmark}</li>
                ))}
              </ul>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-blue-400 mb-3">Sources</h3>
              <ul className="space-y-1">
                {activeCategory.sources.map((source, index) => (
                  <li key={index} className="text-gray-300">• {source}</li>
                ))}
              </ul>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-green-400 mb-3">Methodology</h3>
              <p className="text-gray-300 text-sm">{activeCategory.methodology}</p>
            </div>
          </div>
        </div>

        {/* Performance Rankings */}
        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-2xl font-semibold mb-6">
            {activeCategory.name} Rankings ({sortedModels.length} models)
          </h2>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-4 px-4 text-gray-400 font-medium">RANK</th>
                  <th className="text-left py-4 px-4 text-gray-400 font-medium">MODEL</th>
                  <th className="text-left py-4 px-4 text-gray-400 font-medium">
                    {activeCategory.name === 'Overall' ? 'OVERALL SCORE' : `${activeCategory.name.toUpperCase()} SCORE`}
                  </th>
                  {activeCategory.name === 'Code' && (
                    <>
                      <th className="text-left py-4 px-4 text-gray-400 font-medium">HUMANEVAL</th>
                      <th className="text-left py-4 px-4 text-gray-400 font-medium">MBPP</th>
                      <th className="text-left py-4 px-4 text-gray-400 font-medium">APPS</th>
                    </>
                  )}
                  <th className="text-left py-4 px-4 text-gray-400 font-medium">BENCHMARKS</th>
                  <th className="text-left py-4 px-4 text-gray-400 font-medium">DETAILS</th>
                </tr>
              </thead>
              <tbody>
                {sortedModels.slice(0, 50).map((model, index) => {
                  const rank = index + 1;
                  const score = activeCategory.name === 'Overall' ? model.overall : model[activeCategory.scoreKey] as number;
                  
                  // Extract individual benchmark scores for Code category
                  let humanEval = '-';
                  let mbpp = '-';
                  let apps = '-';
                  
                  if (activeCategory.name === 'Code' && model.code_benchmarks) {
                    // Find the benchmark scores
                    Object.entries(model.code_benchmarks).forEach(([key, value]) => {
                      if (key.toLowerCase().includes('humaneval')) {
                        humanEval = value.toFixed(1);
                      } else if (key.toLowerCase().includes('mbpp')) {
                        mbpp = value.toFixed(1);
                      } else if (key.toLowerCase().includes('apps')) {
                        apps = value.toFixed(1);
                      }
                    });
                  }
                  
                  return (
                    <tr key={model.model} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                      <td className="py-4 px-4">
                        <div className="flex items-center">
                          <span className="text-2xl mr-2">{getRankMedal(rank)}</span>
                          <span className="text-lg font-semibold">{rank}</span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <Link href={`/model/${encodeURIComponent(model.model)}`}>
                          <div className="font-semibold text-lg hover:text-purple-400 transition-colors cursor-pointer">
                            {model.model.replace(/-/g, ' ').toUpperCase()}
                          </div>
                        </Link>
                      </td>
                      <td className="py-4 px-4">
                        <span className={`text-xl font-bold ${
                          rank === 1 ? 'text-yellow-400' :
                          rank === 2 ? 'text-gray-300' :
                          rank === 3 ? 'text-orange-400' :
                          'text-white'
                        }`}>
                          {formatScore(score)}
                        </span>
                      </td>
                      {activeCategory.name === 'Code' && (
                        <>
                          <td className="py-4 px-4">
                            <span className="text-gray-300">{humanEval}</span>
                          </td>
                          <td className="py-4 px-4">
                            <span className="text-gray-300">{mbpp}</span>
                          </td>
                          <td className="py-4 px-4">
                            <span className="text-gray-300">{apps}</span>
                          </td>
                        </>
                      )}
                      <td className="py-4 px-4">
                        <span className="text-gray-300">{model.benchmark_count} total</span>
                      </td>
                      <td className="py-4 px-4">
                        <Link href={`/model/${encodeURIComponent(model.model)}`}>
                          <button className="bg-purple-600 hover:bg-purple-700 px-3 py-1 rounded text-sm transition-colors">
                            View Details
                          </button>
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Stats Footer */}
          <div className="mt-8 pt-6 border-t border-gray-700">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
              <div>
                <div className="text-2xl font-bold text-purple-400">{models.length}</div>
                <div className="text-gray-400">Total Models</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-blue-400">15</div>
                <div className="text-gray-400">Leaderboards</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-400">10</div>
                <div className="text-gray-400">Categories</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-yellow-400">248</div>
                <div className="text-gray-400">Benchmarks</div>
              </div>
            </div>
          </div>
        </div>

        {/* Methodology Section */}
        <div className="bg-gray-800 rounded-xl p-6 mt-8 mb-8">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-3">
            <span className="text-2xl">🔬</span>
            Meta-Leaderboard Methodology
          </h2>
          
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-purple-400 mb-3">Data Collection</h3>
              <p className="text-gray-300">
                We aggregate scores from 15 major LLM evaluation platforms, collecting 248 benchmark data points 
                across 84 models. Data is refreshed nightly to ensure current rankings.
              </p>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-blue-400 mb-3">Scoring System</h3>
              <p className="text-gray-300">
                Each category score is calculated as the weighted average of relevant benchmarks. The overall score 
                combines all category performances, normalized by benchmark participation to ensure fair comparison.
              </p>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-green-400 mb-3">Global Ranking</h3>
              <p className="text-gray-300">
                Models are ranked by their composite score across all participated benchmarks. This provides a 
                comprehensive view of model capabilities while accounting for different evaluation coverage.
              </p>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-yellow-400 mb-3">Data Sources</h3>
              <p className="text-gray-300">
                HuggingFace Open LLM, LMSYS Chatbot Arena, Stanford HELM, BigCode, Scale AI, Vectara, 
                Open Medical LLM, LegalBench, Multilingual LLM, C-Eval, EQ-Bench, AlpacaEval, Finance LLM, 
                Vellum AI, and OpenRouter usage metrics.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 