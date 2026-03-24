import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

interface ModelDetail {
  model_name: string;
  composite_score: number;
  confidence_score: number;
  domain_coverage: string;
  domain_breakdown: {
    [key: string]: {
      domain_score: number;
      confidence: number;
      benchmark_count: number;
      weight_in_profile: number;
      contribution: number;
    };
  };
  missing_domains: string[];
  profile_weights: { [key: string]: number };
}

interface ConsumerModelData {
  name: string;
  overall_rating: number;
  confidence: number;
  rank: number;
  best_for_category: string;
  capabilities: {
    [domain: string]: {
      score: number;
      friendly_name: string;
      description: string;
    };
  };
  pros: string[];
  cons: string[];
  pricing_info: string;
  speed_info: string;
  access_info: string;
  mobile_support: string;
  try_link: string;
}

const getDomainFriendlyName = (domain: string): string => {
  const names = {
    academic: 'Research & Study',
    reasoning: 'Logical Reasoning',
    software_engineering: 'Programming & Code',
    comprehensive: 'General Knowledge',
    medical: 'Healthcare & Medicine',
    legal: 'Legal Analysis'
  };
  return names[domain as keyof typeof names] || domain.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
};

const getDomainDescription = (domain: string): string => {
  const descriptions = {
    academic: 'Research, academic writing, and scholarly analysis',
    reasoning: 'Logic, problem-solving, and analytical thinking',
    software_engineering: 'Code generation, debugging, and technical documentation',
    comprehensive: 'General knowledge, conversation, and everyday tasks',
    medical: 'Medical knowledge, healthcare reasoning, and clinical analysis',
    legal: 'Legal research, document analysis, and jurisprudence'
  };
  return descriptions[domain as keyof typeof descriptions] || 'Specialized domain expertise';
};

const transformToConsumerData = (detail: ModelDetail, profile: string): ConsumerModelData => {
  // Transform technical data to consumer-friendly format
  const name = detail.model_name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  
  const capabilities = Object.entries(detail.domain_breakdown).reduce((acc: { [key: string]: { score: number; friendly_name: string; description: string } }, [domain, data]) => {
    acc[domain] = {
      score: data.domain_score,
      friendly_name: getDomainFriendlyName(domain),
      description: getDomainDescription(domain)
    };
    return acc;
  }, {});

  // Generate pros based on strong domains
  const pros = [];
  Object.entries(capabilities).forEach(([domain, capability]) => {
    if (capability.score >= 80) {
      pros.push(`Excellent ${capability.friendly_name.toLowerCase()} performance`);
    } else if (capability.score >= 70) {
      pros.push(`Strong ${capability.friendly_name.toLowerCase()} capabilities`);
    }
  });
  
  if (detail.confidence_score >= 0.8) pros.push('Highly reliable and consistent results');
  if (detail.domain_coverage === '6/6') pros.push('Complete domain coverage across all areas');
  if (pros.length === 0) pros.push('Well-rounded AI assistant', 'Tested across multiple benchmarks');

  // Generate cons based on weak areas
  const cons = [];
  if (detail.missing_domains.length > 0) {
    cons.push(`Limited coverage in ${detail.missing_domains.join(', ')} domains`);
  }
  if (detail.confidence_score < 0.6) cons.push('Lower confidence in some evaluations');
  Object.entries(capabilities).forEach(([domain, capability]) => {
    if (capability.score < 50) {
      cons.push(`Weaker ${capability.friendly_name.toLowerCase()} performance`);
    }
  });

  // Mock practical information (would come from real data sources)
  const getPricingInfo = (name: string): string => {
    if (name.toLowerCase().includes('gpt-4')) return 'Premium pricing - $20-30/month for full access';
    if (name.toLowerCase().includes('claude')) return 'Competitive pricing - $15-25/month';
    if (name.toLowerCase().includes('gemini')) return 'Google pricing - Free tier available, $10-20/month for Pro';
    return 'Varies by provider - Check official website for current pricing';
  };

  const getSpeedInfo = (name: string): string => {
    if (name.toLowerCase().includes('mini') || name.toLowerCase().includes('flash')) return 'Very fast response times (1-3 seconds)';
    if (name.toLowerCase().includes('pro') || name.toLowerCase().includes('max')) return 'Fast response times (3-5 seconds)';
    return 'Standard response times (5-10 seconds)';
  };

  const getAccessInfo = (name: string): string => {
    if (name.toLowerCase().includes('gpt')) return 'Available via ChatGPT, API, and third-party apps';
    if (name.toLowerCase().includes('claude')) return 'Available via Claude.ai and API';
    if (name.toLowerCase().includes('gemini')) return 'Available via Google AI Studio and API';
    return 'Check provider for access options';
  };

  const getTryLink = (name: string): string => {
    if (name.toLowerCase().includes('gpt')) return 'https://chat.openai.com';
    if (name.toLowerCase().includes('claude')) return 'https://claude.ai';
    if (name.toLowerCase().includes('gemini')) return 'https://gemini.google.com';
    return '#';
  };

  return {
    name,
    overall_rating: detail.composite_score,
    confidence: detail.confidence_score,
    rank: 1, // Would be calculated from leaderboard position
    best_for_category: profile,
    capabilities,
    pros,
    cons,
    pricing_info: getPricingInfo(name),
    speed_info: getSpeedInfo(name),
    access_info: getAccessInfo(name),
    mobile_support: 'Mobile web support - check app availability',
    try_link: getTryLink(name)
  };
};

export default function ModelDetail() {
  const router = useRouter();
  const { id, profile = 'general' } = router.query;
  const [modelData, setModelData] = useState<ConsumerModelData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id && typeof id === 'string') {
      fetchModelDetail(id, profile as string);
    }
  }, [id, profile]);

  const fetchModelDetail = async (modelName: string, profileName: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v3/composite/model/${encodeURIComponent(modelName)}?profile_name=${profileName}`);
      
      if (!response.ok) {
        throw new Error(`Model not found: ${response.statusText}`);
      }

      const data: ModelDetail = await response.json();
      const consumerData = transformToConsumerData(data, profileName);
      setModelData(consumerData);
    } catch (err) {
      console.error('Error fetching model detail:', err);
      setError('Model not found or temporarily unavailable.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-lg text-gray-600">Loading model details...</div>
        </div>
      </div>
    );
  }

  if (error || !modelData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">🤖</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Model not found</h2>
          <p className="text-gray-600 mb-4">{error || 'This AI model could not be found or is not available.'}</p>
          <div className="flex gap-3 justify-center">
            <button 
              onClick={() => router.back()}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
            >
              Go Back
            </button>
            <Link 
              href="/"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Browse All Models
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between mb-6">
            <button 
              onClick={() => router.back()}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
            >
              ← Back
            </button>
            <div className="text-sm text-gray-500">
              AI Model Review
            </div>
          </div>

          <div className="flex flex-col md:flex-row md:items-center justify-between">
            <div className="mb-4 md:mb-0">
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
                {modelData.name}
              </h1>
              <div className="flex items-center gap-4 mb-2">
                <div className="flex items-center">
                  <span className="text-2xl font-bold text-yellow-500 mr-2">
                    {modelData.overall_rating.toFixed(1)}
                  </span>
                  <span className="text-gray-600">/ 5.0</span>
                </div>
                <span className="text-2xl font-bold text-gray-900">
                  {Math.round(modelData.overall_rating)}/100 Overall Rating
                </span>
              </div>
              <div className="inline-flex items-center bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                🏆 #{modelData.rank} choice for {profile}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Capabilities Section */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                📊 What this AI is great at:
              </h2>
              
              <div className="space-y-4">
                {Object.entries(modelData.capabilities).map(([domain, capability]) => (
                  <div key={domain} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-gray-900">{capability.friendly_name}</h3>
                      <div className="flex items-center gap-2">
                        <div className="w-32 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${Math.min(capability.score, 100)}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-700 w-12">
                          {Math.round(capability.score)}/100
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600">{capability.description}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Pros and Cons */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-green-50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-green-900 mb-4 flex items-center gap-2">
                  ✅ Pros:
                </h3>
                <ul className="space-y-2">
                  {modelData.pros.map((pro, index) => (
                    <li key={index} className="flex items-start gap-2 text-green-800">
                      <span className="text-green-600 mt-0.5">•</span>
                      <span>{pro}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="bg-orange-50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-orange-900 mb-4 flex items-center gap-2">
                  ❌ Cons:
                </h3>
                {modelData.cons.length > 0 ? (
                  <ul className="space-y-2">
                    {modelData.cons.map((con, index) => (
                      <li key={index} className="flex items-start gap-2 text-orange-800">
                        <span className="text-orange-600 mt-0.5">•</span>
                        <span>{con}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-orange-800">No significant limitations identified</p>
                )}
              </div>
            </div>

            {/* Practical Information */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">Practical Information</h3>
              
              <div className="grid md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">💰</span>
                    <div>
                      <div className="font-medium text-gray-900">Pricing</div>
                      <div className="text-sm text-gray-600">{modelData.pricing_info}</div>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">⚡</span>
                    <div>
                      <div className="font-medium text-gray-900">Speed</div>
                      <div className="text-sm text-gray-600">{modelData.speed_info}</div>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">🔗</span>
                    <div>
                      <div className="font-medium text-gray-900">Access</div>
                      <div className="text-sm text-gray-600">{modelData.access_info}</div>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <span className="text-2xl">📱</span>
                    <div>
                      <div className="font-medium text-gray-900">Mobile</div>
                      <div className="text-sm text-gray-600">{modelData.mobile_support}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-6 text-white">
              <h3 className="text-xl font-semibold mb-4">Ready to try {modelData.name}?</h3>
              <div className="flex flex-col sm:flex-row gap-3">
                <a 
                  href={modelData.try_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center px-6 py-3 bg-white text-blue-600 font-medium rounded-lg hover:bg-gray-100 transition-colors"
                >
                  Start Using This AI
                </a>
                <Link 
                  href="/compare"
                  className="inline-flex items-center justify-center px-6 py-3 border border-white text-white font-medium rounded-lg hover:bg-white hover:text-blue-600 transition-colors"
                >
                  See Alternatives
                </Link>
                <Link 
                  href="/results"
                  className="inline-flex items-center justify-center px-6 py-3 text-white font-medium rounded-lg hover:bg-white/10 transition-colors"
                >
                  Compare All Models
                </Link>
              </div>
            </div>

            {/* Advanced Section (Progressive Disclosure) */}
            <div className="bg-white rounded-xl shadow-sm">
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="w-full p-6 text-left border-b border-gray-200 hover:bg-gray-50 transition-colors"
              >
                <h3 className="text-lg font-semibold text-gray-900 flex items-center justify-between">
                  🔬 Technical Details (for experts)
                  <span className="text-gray-400">{showAdvanced ? '−' : '+'}</span>
                </h3>
              </button>
              
              {showAdvanced && (
                <div className="p-6">
                  <div className="grid md:grid-cols-2 gap-6">
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">Evaluation Confidence</h4>
                      <p className="text-sm text-gray-600 mb-4">
                        {Math.round(modelData.confidence * 100)}% confidence in scoring based on benchmark coverage
                      </p>
                      
                      <h4 className="font-medium text-gray-900 mb-2">Domain Coverage</h4>
                      <p className="text-sm text-gray-600">
                        Evaluated across {Object.keys(modelData.capabilities).length}/6 professional domains
                      </p>
                    </div>
                    
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">Methodology</h4>
                      <p className="text-sm text-gray-600 mb-2">
                        • Research-grade benchmark evaluation
                      </p>
                      <p className="text-sm text-gray-600 mb-2">
                        • Professional domain weighting
                      </p>
                      <p className="text-sm text-gray-600">
                        • Statistical confidence scoring
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Summary */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Summary</h3>
              
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Overall Rating</span>
                  <span className="font-semibold">{Math.round(modelData.overall_rating)}/100</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Ranking</span>
                  <span className="font-semibold">#{modelData.rank}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Best for</span>
                  <span className="font-semibold capitalize">{profile}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Reliability</span>
                  <span className="font-semibold">
                    {modelData.confidence >= 0.8 ? 'Excellent' : 
                     modelData.confidence >= 0.6 ? 'Good' : 'Fair'}
                  </span>
                </div>
              </div>
            </div>

            {/* Alternative Profiles */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">See other rankings</h3>
              
              <div className="space-y-2">
                {['general', 'academic', 'developer', 'healthcare', 'legal'].map((p) => (
                  <Link
                    key={p}
                    href={`/model/${id}?profile=${p}`}
                    className={`block w-full px-4 py-2 text-left font-medium rounded-md transition-colors ${
                      p === profile 
                        ? 'bg-blue-600 text-white' 
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    {p.charAt(0).toUpperCase() + p.slice(1)} Profile
                  </Link>
                ))}
              </div>
            </div>

            {/* Related Models */}
            <div className="bg-gray-100 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Similar Models</h3>
              
              <div className="text-center py-4">
                <div className="text-2xl mb-2">🔄</div>
                <div className="text-sm text-gray-600">
                  Model comparison coming soon...
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 