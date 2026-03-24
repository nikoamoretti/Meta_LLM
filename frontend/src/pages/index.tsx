import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

interface CategoryChip {
  slug: string;
  name: string;
  icon: string;
  description: string;
}

const categories: CategoryChip[] = [
  { slug: 'general', name: 'General', icon: '🤖', description: 'All-purpose AI assistance' },
  { slug: 'coding', name: 'Coding', icon: '💻', description: 'Programming & development' },
  { slug: 'research', name: 'Research', icon: '🎓', description: 'Academic & scientific work' },
  { slug: 'creative', name: 'Creative', icon: '🎨', description: 'Writing & content creation' },
  { slug: 'business', name: 'Business', icon: '📊', description: 'Professional & enterprise' },
  { slug: 'medical', name: 'Medical', icon: '⚕️', description: 'Healthcare & medicine' },
  { slug: 'legal', name: 'Legal', icon: '⚖️', description: 'Law & compliance' },
  { slug: 'finance', name: 'Finance', icon: '💰', description: 'Financial analysis' },
  { slug: 'chat', name: 'Chat', icon: '💬', description: 'Conversational AI' }
];

export default function Home() {
  const router = useRouter();
  const [stats, setStats] = useState({ totalModels: 265, totalBenchmarks: 50, domains: 20 });

  // Load stats asynchronously without blocking page render
  useEffect(() => {
    const loadStats = async () => {
      try {
        const response = await fetch('/api/v3/stats/quick');
        const data = await response.json();
        if (data.status === 'success') {
          const quickStats = data.data;
          setStats({
            totalModels: quickStats.total_models,
            totalBenchmarks: quickStats.benchmarks,
            domains: quickStats.domains
          });
        }
      } catch (error) {
        // Silently fail and keep default stats - page still loads instantly
        console.log('Stats loading failed, using defaults');
      }
    };
    
    // Load stats after page renders to avoid blocking
    setTimeout(loadStats, 50);
  }, []);

  return (
    <div className="min-h-screen bg-white">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-blue-600 via-purple-600 to-indigo-700 text-white">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="text-center mb-12">
            <h1 className="text-5xl md:text-6xl font-bold mb-6">
              🤖 Find Your Perfect AI Assistant
            </h1>
            <p className="text-xl md:text-2xl text-blue-100 mb-8 max-w-3xl mx-auto">
              Simple recommendations for what you actually want to do
            </p>
            <div className="inline-flex items-center bg-white/10 backdrop-blur-sm rounded-full px-6 py-3">
              <span className="text-blue-100">
                Comparing {stats.totalModels} AI models across {stats.domains} professional domains
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Navigation Section */}
      <div className="max-w-7xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            What do you want to use AI for?
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Choose your exploration path to find the perfect AI model
          </p>
        </div>

        {/* Two Big Buttons */}
        <div className="flex flex-col sm:flex-row gap-6 justify-center mb-16">
          <Link href="/simple-models">
            <button className="group bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold py-6 px-12 rounded-2xl text-xl transition-all duration-200 transform hover:scale-105 shadow-xl hover:shadow-2xl">
              <div className="flex items-center justify-center space-x-3">
                <span className="text-2xl">🏆</span>
                <span>See Coding Rankings</span>
                <span className="group-hover:translate-x-1 transition-transform">→</span>
              </div>
              <p className="text-blue-100 text-sm mt-2 font-normal">
                Fresh coding benchmark results from Aider & SWE-Bench
              </p>
            </button>
          </Link>
          
          <button 
            onClick={() => {
              const categorySection = document.getElementById('category-chips');
              categorySection?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="group bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-bold py-6 px-12 rounded-2xl text-xl transition-all duration-200 transform hover:scale-105 shadow-xl hover:shadow-2xl"
          >
            <div className="flex items-center justify-center space-x-3">
              <span className="text-2xl">🎯</span>
              <span>Choose by Category</span>
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </div>
            <p className="text-purple-100 text-sm mt-2 font-normal">
              Find specialists for your specific needs
            </p>
          </button>
        </div>

        {/* Horizontal Category Chips */}
        <div id="category-chips" className="mb-16">
          <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            Browse by Category
          </h3>
          <div className="overflow-x-auto pb-4">
            <div className="flex space-x-4 min-w-max px-4">
              {categories.map((category) => (
                <Link key={category.slug} href={`/category/${category.slug}`}>
                  <div className="group cursor-pointer bg-white rounded-xl shadow-md border border-gray-200 hover:border-blue-300 hover:shadow-lg transition-all duration-200 p-6 min-w-[200px] transform hover:scale-105">
                    <div className="text-center">
                      <div className="text-3xl mb-3">{category.icon}</div>
                      <h4 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors mb-2">
                        {category.name}
                      </h4>
                      <p className="text-sm text-gray-600">
                        {category.description}
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>

        {/* Trust Indicators */}
        <div className="mt-16 text-center">
          <h3 className="text-xl font-semibold text-gray-900 mb-8">
            Trusted by professionals worldwide
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600">{stats.totalModels}+</div>
              <div className="text-gray-600">AI Models</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600">{stats.totalBenchmarks}+</div>
              <div className="text-gray-600">Benchmarks</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-indigo-600">{stats.domains}</div>
              <div className="text-gray-600">Professional Domains</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">100%</div>
              <div className="text-gray-600">Research Grade</div>
            </div>
          </div>
        </div>

        {/* How it Works */}
        <div className="mt-20">
          <div className="text-center mb-12">
            <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">
              How we help you choose
            </h3>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Our AI recommendation system is like Consumer Reports for artificial intelligence
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="bg-blue-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🔍</span>
              </div>
              <h4 className="text-xl font-semibold text-gray-900 mb-2">Comprehensive Testing</h4>
              <p className="text-gray-600">
                We test every AI model across 50+ professional benchmarks to give you reliable, research-grade evaluations.
              </p>
            </div>
            <div className="text-center">
              <div className="bg-purple-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">⭐</span>
              </div>
              <h4 className="text-xl font-semibold text-gray-900 mb-2">Simple Ratings</h4>
              <p className="text-gray-600">
                Complex benchmark scores become easy-to-understand star ratings, so you can compare models at a glance.
              </p>
            </div>
            <div className="text-center">
              <div className="bg-green-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🎯</span>
              </div>
              <h4 className="text-xl font-semibold text-gray-900 mb-2">Personalized Recommendations</h4>
              <p className="text-gray-600">
                Get recommendations tailored to your specific use case, whether you're coding, writing, or researching.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer CTA */}
      <div className="bg-gray-900 text-white py-12">
        <div className="max-w-4xl mx-auto text-center px-6">
          <h3 className="text-2xl font-bold mb-4">Ready to find your perfect AI?</h3>
          <p className="text-gray-300 mb-6">
            Join thousands of professionals who use our recommendations to choose the right AI for their work.
          </p>
          <Link href="/models">
            <button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-xl transition-colors">
              Get Started Now
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
} 