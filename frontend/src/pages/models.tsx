import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

interface ModelRanking {
  model_name: string;
  composite_score: number;
  confidence_score: number;
  domain_coverage: string;
  rank: number;
  domain_scores: {
    coding?: number;
    reasoning?: number;
    academic?: number;
    medical?: number;
    legal?: number;
    finance?: number;
  };
  last_updated: string;
}

interface SortConfig {
  key: keyof ModelRanking | 'coding' | 'reasoning' | 'academic' | 'medical' | 'legal' | 'finance';
  direction: 'asc' | 'desc';
}

const getScoreBadgeColor = (score: number | undefined): string => {
  if (!score) return 'bg-gray-100 text-gray-600';
  if (score >= 90) return 'bg-green-100 text-green-800';
  if (score >= 70) return 'bg-amber-100 text-amber-800';
  return 'bg-rose-100 text-rose-600';
};

const ScoreBadge: React.FC<{ score: number | undefined }> = ({ score }) => {
  if (!score) return <span className="text-gray-400 text-sm">—</span>;
  
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-md text-sm font-medium ${getScoreBadgeColor(score)}`}>
      {score.toFixed(1)}
    </span>
  );
};

export default function ModelsPage() {
  const router = useRouter();
  const [models, setModels] = useState<ModelRanking[]>([]);
  const [filteredModels, setFilteredModels] = useState<ModelRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'composite_score', direction: 'desc' });
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilters, setActiveFilters] = useState<Record<string, string[]>>({});

  useEffect(() => {
    fetchModels();
  }, []);

  useEffect(() => {
    // Update URL with sort params
    const query: any = {};
    if (sortConfig.key !== 'composite_score' || sortConfig.direction !== 'desc') {
      query.sort = sortConfig.key;
      query.dir = sortConfig.direction;
    }
    
    router.replace({
      pathname: '/models',
      query
    }, undefined, { shallow: true });
  }, [sortConfig]);

  useEffect(() => {
    // Read sort params from URL on page load
    if (router.query.sort) {
      setSortConfig({
        key: router.query.sort as any,
        direction: (router.query.dir as 'asc' | 'desc') || 'desc'
      });
    }
  }, [router.query]);

  const fetchModels = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v3/composite/leaderboard/General?limit=100');
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch models');
      }

      // Transform data to match our interface
      const transformedModels: ModelRanking[] = data.leaderboard.map((model: any, index: number) => ({
        model_name: model.model_name,
        composite_score: model.composite_score,
        confidence_score: model.confidence_score,
        domain_coverage: model.domain_coverage,
        rank: index + 1,
        domain_scores: {
          coding: model.domain_scores?.software_engineering || model.domain_scores?.coding,
          reasoning: model.domain_scores?.reasoning,
          academic: model.domain_scores?.academic,
          medical: model.domain_scores?.medical,
          legal: model.domain_scores?.legal,
          finance: model.domain_scores?.finance
        },
        last_updated: model.last_updated || new Date().toISOString()
      }));

      setModels(transformedModels);
      setFilteredModels(transformedModels);
    } catch (err) {
      console.error('Error fetching models:', err);
      setError(err instanceof Error ? err.message : 'Failed to load models');
    } finally {
      setLoading(false);
    }
  };

  // Apply search and filters
  useEffect(() => {
    let filtered = [...models];

    // Apply search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(model => 
        model.model_name.toLowerCase().includes(query) ||
        // Add more searchable fields if available
        Object.values(model.domain_scores).some(score => 
          score && score.toString().includes(query)
        )
      );
    }

    // Apply filters (simplified - would need actual model metadata)
    // This is a placeholder implementation
    Object.keys(activeFilters).forEach(filterType => {
      const filterValues = activeFilters[filterType];
      if (filterValues.length > 0) {
        // For demo purposes, just filter by model name patterns
        if (filterType === 'provider') {
          filtered = filtered.filter(model =>
            filterValues.some(provider =>
              model.model_name.toLowerCase().includes(provider.toLowerCase())
            )
          );
        }
      }
    });

    setFilteredModels(filtered);
  }, [models, searchQuery, activeFilters]);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleFilter = (filters: Record<string, string[]>) => {
    setActiveFilters(filters);
  };

  const handleSort = (key: SortConfig['key']) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
    }));
  };

  const getSortedModels = () => {
    return [...filteredModels].sort((a, b) => {
      let aValue: any, bValue: any;

      if (['coding', 'reasoning', 'academic', 'medical', 'legal', 'finance'].includes(sortConfig.key as string)) {
        aValue = a.domain_scores[sortConfig.key as keyof typeof a.domain_scores] || 0;
        bValue = b.domain_scores[sortConfig.key as keyof typeof b.domain_scores] || 0;
      } else {
        aValue = a[sortConfig.key as keyof ModelRanking];
        bValue = b[sortConfig.key as keyof ModelRanking];
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        aValue = aValue.toLowerCase();
        bValue = bValue.toLowerCase();
      }

      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  };

  const SortIcon: React.FC<{ column: string }> = ({ column }) => {
    if (sortConfig.key !== column) {
      return <span className="text-gray-400">↕</span>;
    }
    return <span className="text-blue-600">{sortConfig.direction === 'desc' ? '↓' : '↑'}</span>;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading global rankings...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">⚠️ Error</div>
          <p className="text-gray-600">{error}</p>
          <button 
            onClick={fetchModels}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const sortedModels = getSortedModels();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Global AI Model Rankings</h1>
              <p className="text-gray-600">
                Comprehensive evaluation across all professional domains
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/methodology" className="text-blue-600 hover:text-blue-800 font-medium">
                Methodology
              </Link>
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
                <strong>{filteredModels.length}</strong> of <strong>{models.length}</strong> models shown
              </span>
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                Updated: {new Date().toLocaleDateString()}
              </span>
              <Link href="/methodology" className="text-blue-700 underline hover:no-underline">
                Methodology: Composite Z-Score
              </Link>
            </div>
          </div>
        </div>
      </div>


      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 pb-8">
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th 
                    scope="col" 
                    className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('rank')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Rank</span>
                      <SortIcon column="rank" />
                    </div>
                  </th>
                  <th 
                    scope="col" 
                    className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('model_name')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Model</span>
                      <SortIcon column="model_name" />
                    </div>
                  </th>
                  <th 
                    scope="col" 
                    className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('composite_score')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>★ Composite</span>
                      <SortIcon column="composite_score" />
                    </div>
                  </th>
                  <th 
                    scope="col" 
                    className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('coding')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Code</span>
                      <SortIcon column="coding" />
                    </div>
                  </th>
                  <th 
                    scope="col" 
                    className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('reasoning')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Reasoning</span>
                      <SortIcon column="reasoning" />
                    </div>
                  </th>
                  <th 
                    scope="col" 
                    className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('academic')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Academic</span>
                      <SortIcon column="academic" />
                    </div>
                  </th>
                  <th 
                    scope="col" 
                    className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('medical')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Medical</span>
                      <SortIcon column="medical" />
                    </div>
                  </th>
                  <th 
                    scope="col" 
                    className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('legal')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Legal</span>
                      <SortIcon column="legal" />
                    </div>
                  </th>
                  <th 
                    scope="col" 
                    className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('finance')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Finance</span>
                      <SortIcon column="finance" />
                    </div>
                  </th>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Updated
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sortedModels.map((model, index) => (
                  <tr key={model.model_name} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      #{model.rank}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link 
                        href={`/model/${encodeURIComponent(model.model_name)}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {model.model_name}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg font-bold text-gray-900">
                          {model.composite_score.toFixed(1)}
                        </span>
                        <span className="text-xs text-gray-500">
                          ({model.domain_coverage})
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <ScoreBadge score={model.domain_scores.coding} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <ScoreBadge score={model.domain_scores.reasoning} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <ScoreBadge score={model.domain_scores.academic} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <ScoreBadge score={model.domain_scores.medical} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <ScoreBadge score={model.domain_scores.legal} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <ScoreBadge score={model.domain_scores.finance} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(model.last_updated).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Methodology Footer */}
        <div className="mt-8 bg-blue-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">About These Rankings</h3>
          <p className="text-blue-800 mb-4">
            Composite scores are calculated using a confidence-weighted average across multiple professional domains. 
            Higher scores indicate better performance, with 90+ being excellent, 70-89 good, and below 70 needing improvement.
          </p>
          <div className="flex space-x-4 text-sm">
            <button className="text-blue-600 hover:text-blue-800 underline">
              Learn about methodology
            </button>
            <button className="text-blue-600 hover:text-blue-800 underline">
              View by category
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}