import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

interface CompositeModel {
  model_name: string;
  composite_score: number;
  confidence_score: number;
  domain_coverage: string;
  rank?: number;
}

interface CompositeResponse {
  profile_name: string;
  total_models: number;
  leaderboard: CompositeModel[];
}

interface ModelData extends CompositeModel {
  best_for: string;
  cost_tier: string;
  speed_tier: string;
  reliability_tier: string;
  pros: string[];
  cons: string[];
  try_link: string;
  strengths: string;
}

const getRankEmoji = (rank: number): string => {
  if (rank === 1) return '🥇';
  if (rank === 2) return '🥈';
  if (rank === 3) return '🥉';
  return '🔢';
};

const getProfileDisplayName = (profile: string): string => {
  const names = {
    general: 'General Use & Business',
    academic: 'Research & Study',
    developer: 'Coding & Tech',
    healthcare: 'Healthcare & Medical',
    legal: 'Legal & Jurisprudence'
  };
  return names[profile as keyof typeof names] || 'General Use';
};

const getProfileDescription = (profile: string): string => {
  const descriptions = {
    general: 'Best AI models for everyday tasks, business work, and general conversations',
    academic: 'Top performers for research, studying, academic writing, and educational content',
    developer: 'Leading models for programming, debugging, code review, and technical documentation',
    healthcare: 'Specialized models for medical knowledge, healthcare reasoning, and clinical applications',
    legal: 'Expert models for legal research, document analysis, and jurisprudence understanding'
  };
  return descriptions[profile as keyof typeof descriptions] || 'Best AI models for your needs';
};

// Mock data transformation functions (these would normally fetch from APIs)
const transformToConsumerData = (model: CompositeModel, profile: string): ModelData => {
  // This would normally integrate with pricing/feature APIs
  const getCostTier = (name: string): string => {
    if (name.toLowerCase().includes('gpt-4') || name.toLowerCase().includes('claude')) return '$$$';
    if (name.toLowerCase().includes('gemini') || name.toLowerCase().includes('sonnet')) return '$$';
    return '$';
  };

  const getSpeedTier = (name: string): string => {
    if (name.toLowerCase().includes('mini') || name.toLowerCase().includes('flash')) return 'Very Fast';
    if (name.toLowerCase().includes('pro') || name.toLowerCase().includes('max')) return 'Fast';
    return 'Standard';
  };

  const getBestFor = (score: number, profile: string): string => {
    const profileBestFor = {
      general: 'Everyday tasks and business work',
      academic: 'Research and academic writing',
      developer: 'Programming and code review',
      healthcare: 'Medical knowledge and reasoning',
      legal: 'Legal research and analysis'
    };
    return profileBestFor[profile as keyof typeof profileBestFor] || 'General purpose tasks';
  };

  const getStrengths = (name: string, profile: string): string => {
    // Simplified logic - would be more sophisticated with real data
    if (profile === 'developer') return 'Code generation, debugging, technical explanations';
    if (profile === 'academic') return 'Research, analysis, academic writing';
    if (profile === 'healthcare') return 'Medical knowledge, clinical reasoning';
    if (profile === 'legal') return 'Legal analysis, document review';
    return 'Versatile AI for multiple tasks';
  };

  const getTryLink = (name: string): string => {
    // Map to actual platform links
    if (name.toLowerCase().includes('gpt')) return 'https://chat.openai.com';
    if (name.toLowerCase().includes('claude')) return 'https://claude.ai';
    if (name.toLowerCase().includes('gemini')) return 'https://gemini.google.com';
    return '#';
  };

  return {
    ...model,
    best_for: getBestFor(model.composite_score, profile),
    cost_tier: getCostTier(model.model_name),
    speed_tier: getSpeedTier(model.model_name),
    reliability_tier: model.confidence_score > 0.8 ? 'Excellent' : model.confidence_score > 0.6 ? 'Good' : 'Fair',
    pros: [`High ${profile} performance`, 'Reliable results', 'Well-tested'],
    cons: model.domain_coverage !== '6/6' ? ['Limited domain coverage'] : [],
    try_link: getTryLink(model.model_name),
    strengths: getStrengths(model.model_name, profile)
  };
};

export default function Results() {
  const router = useRouter();
  const { profile = 'general' } = router.query;
  const [models, setModels] = useState<ModelData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (profile) {
      fetchCompositeModels(profile as string);
    }
  }, [profile]);

  const fetchCompositeModels = async (profileName: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v3/composite/leaderboard/${profileName}?limit=50`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch models: ${response.statusText}`);
      }

      const data: CompositeResponse = await response.json();
      
      // Transform technical data to consumer-friendly format
      const consumerModels = data.leaderboard.map((model, index) => ({
        ...transformToConsumerData(model, profileName),
        rank: index + 1
      }));

      setModels(consumerModels);
    } catch (err) {
      console.error('Error fetching composite models:', err);
      setError('Failed to load AI model recommendations. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-lg text-gray-600">Finding the best AI models for you...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Oops! Something went wrong</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={() => router.back()}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
                🏆 Best AI Models for {getProfileDisplayName(profile as string)}
              </h1>
              <p className="text-lg text-gray-600">
                {getProfileDescription(profile as string)}
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/methodology" className="text-blue-600 hover:text-blue-800 font-medium">
                Methodology
              </Link>
              <button 
                onClick={() => router.push('/')}
                className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg transition-colors"
              >
                ← Back to Home
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Main Results */}
          <div className="flex-1">
            <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">
                  Top {models.length} Recommendations
                </h2>
                <div className="mt-2">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                    Updated: {new Date().toLocaleDateString()}
                  </span>
                </div>
              </div>
              
              <p className="text-gray-600 mb-6">
                These AI models are ranked by their performance in {profile} tasks using our composite scoring system.
              </p>
            </div>

            {/* Model Cards */}
            <div className="space-y-4">
              {models.map((model) => (
                <div 
                  key={model.model_name} 
                  className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow"
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-2xl">{getRankEmoji(model.rank!)}</span>
                        <div className="flex items-center gap-2">
                          <span className="bg-blue-100 text-blue-800 text-sm font-medium px-2 py-1 rounded">
                            #{model.rank}
                          </span>
                        </div>
                        <div className="flex items-center">
                          <span className="text-lg font-bold text-yellow-500 mr-1">
                            {model.composite_score.toFixed(1)}
                          </span>
                          <span className="text-gray-600">/ 100</span>
                        </div>
                        <span className="text-lg font-semibold text-gray-900">
                          {Math.round(model.composite_score)}/100
                        </span>
                      </div>

                      <h3 className="text-xl font-bold text-gray-900 mb-2">
                        {model.model_name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </h3>
                      
                      <p className="text-gray-600 mb-3">
                        <strong>Best for:</strong> {model.strengths}
                      </p>

                      <div className="flex flex-wrap gap-4 mb-4">
                        <div className="flex items-center gap-1">
                          <span className="text-lg">💰</span>
                          <span className="text-sm text-gray-600">Cost: {model.cost_tier}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-lg">⚡</span>
                          <span className="text-sm text-gray-600">Speed: {model.speed_tier}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-lg">🎯</span>
                          <span className="text-sm text-gray-600">Reliability: {model.reliability_tier}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-lg">📊</span>
                          <span className="text-sm text-gray-600">Coverage: {model.domain_coverage}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-2 mt-4 md:mt-0">
                      <a
                        href={model.try_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg transition-colors text-center"
                      >
                        Try Free
                      </a>
                      <Link href={`/model/${encodeURIComponent(model.model_name)}?profile=${profile}`}>
                        <button className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium px-4 py-2 rounded-lg transition-colors">
                          Learn More
                        </button>
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Show More Button */}
            {models.length >= 20 && (
              <div className="text-center mt-8">
                <button className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium px-6 py-3 rounded-lg transition-colors">
                  Show More Models
                </button>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="lg:w-80">
            {/* Filter Section */}
            <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Refine Results</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Cost Range</label>
                  <div className="space-y-2">
                    {['All', 'Free', 'Budget ($)', 'Premium ($$)', 'Enterprise ($$$)'].map(option => (
                      <label key={option} className="flex items-center">
                        <input type="radio" name="cost" className="mr-2" defaultChecked={option === 'All'} />
                        <span className="text-sm text-gray-600">{option}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Minimum Rating</label>
                  <select className="w-full p-2 border border-gray-300 rounded-lg text-sm">
                    <option>Any rating</option>
                    <option>4+ stars</option>
                    <option>3+ stars</option>
                  </select>
                </div>
              </div>
            </div>

            {/* How Rankings Work */}
            <div className="bg-blue-50 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-blue-900 mb-3">
                💡 How we rank AI models
              </h3>
              <div className="space-y-2 text-sm text-blue-800">
                <p>• <strong>Performance:</strong> Real benchmark results</p>
                <p>• <strong>Specialization:</strong> {profile} task focus</p>
                <p>• <strong>Reliability:</strong> Consistent quality scores</p>
                <p>• <strong>Coverage:</strong> Domain expertise breadth</p>
              </div>
              <div className="mt-4 pt-4 border-t border-blue-200">
                <p className="text-xs text-blue-700">
                  Our rankings are based on research-grade evaluation across 50+ professional benchmarks.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 