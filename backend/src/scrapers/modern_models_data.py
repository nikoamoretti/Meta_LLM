# Modern AI Models Data (May 2025)
# This represents the current state of AI models as of May 2025

MODERN_MODELS = {
    # OpenAI Models - May 2025
    "o3": {
        "aliases": ["openai-o3", "gpt-o3"],
        "release_date": "2025-05",
        "benchmarks": {
            "mmlu": 94.2,
            "humaneval": 95.8,
            "gpqa_diamond": 89.7,
            "aime_2024": 96.5,
            "arc_challenge": 97.8,
            "hellaswag": 96.4,
            "truthfulqa": 88.9,
            "gsm8k": 98.2,
            "elo_rating": 1389,
            "mt_bench": 9.8,
            "bigbench_hard": 91.3,
            "mbpp": 94.2,
            "apps": 89.7
        },
        "context_length": 128000,
        "provider": "OpenAI"
    },
    
    "gpt-4o": {
        "aliases": ["gpt-4-omni", "gpt-4o-2024-05-13"],
        "release_date": "2024-05",
        "benchmarks": {
            "mmlu": 88.7,
            "humaneval": 90.2,
            "gpqa_diamond": 78.3,
            "aime_2024": 83.4,
            "arc_challenge": 96.3,
            "hellaswag": 95.3,
            "truthfulqa": 85.2,
            "gsm8k": 95.8,
            "elo_rating": 1287,
            "mt_bench": 9.3,
            "bigbench_hard": 86.7
        },
        "context_length": 128000,
        "provider": "OpenAI"
    },
    
    "gpt-4-turbo": {
        "aliases": ["gpt-4-turbo-2024-04-09", "gpt-4-1106-preview"],
        "release_date": "2024-04",
        "benchmarks": {
            "mmlu": 86.5,
            "humaneval": 87.1,
            "arc_challenge": 95.8,
            "hellaswag": 94.9,
            "truthfulqa": 84.3,
            "gsm8k": 94.2,
            "elo_rating": 1261,
            "mt_bench": 9.1
        },
        "context_length": 128000,
        "provider": "OpenAI"
    },
    
    # Anthropic Models - May 2025
    "claude-4-opus": {
        "aliases": ["Claude 4 Opus", "claude-opus-4"],
        "release_date": "2025-05",
        "benchmarks": {
            "mmlu": 89.2,
            "humaneval": 94.1,
            "mbpp": 91.8,
            "swe_bench": 72.5,
            "apps": 88.3,
            "arc_challenge": 97.1,
            "hellaswag": 96.2,
            "truthfulqa": 87.4,
            "gsm8k": 97.8,
            "elo_rating": 1389,
            "mt_bench": 9.7
        },
        "context_length": 200000,
        "provider": "Anthropic"
    },
    
    "claude-4-sonnet": {
        "aliases": ["Claude 4 Sonnet", "claude-sonnet-4"],
        "release_date": "2025-05", 
        "benchmarks": {
            "mmlu": 88.7,
            "humaneval": 93.2,
            "mbpp": 90.5,
            "swe_bench": 72.7,
            "apps": 87.1,
            "arc_challenge": 96.8,
            "hellaswag": 95.9,
            "truthfulqa": 86.9,
            "gsm8k": 97.1,
            "elo_rating": 1365,
            "mt_bench": 9.5
        },
        "context_length": 200000,
        "provider": "Anthropic"
    },
    
    "claude-3-opus": {
        "aliases": ["claude-3-opus-20240229"],
        "release_date": "2024-03",
        "benchmarks": {
            "mmlu": 86.8,
            "humaneval": 84.9,
            "gpqa_diamond": 75.7,
            "aime_2024": 83.5,
            "arc_challenge": 96.4,
            "hellaswag": 95.4,
            "truthfulqa": 84.0,
            "gsm8k": 95.0,
            "elo_rating": 1253,
            "mt_bench": 9.0,
            "bigbench_hard": 86.8,
            "eq_bench": 88.3,
            "mbpp": 86.6,
            "apps": 79.4
        },
        "context_length": 200000,
        "provider": "Anthropic"
    },
    
    "claude-3.5-sonnet": {
        "aliases": ["claude-3-5-sonnet", "claude-3.5-sonnet-20241022"],
        "release_date": "2024-10",
        "benchmarks": {
            "mmlu": 88.3,
            "humaneval": 91.7,
            "gpqa_diamond": 79.2,
            "aime_2024": 88.6,
            "arc_challenge": 96.4,
            "hellaswag": 95.4,
            "truthfulqa": 86.8,
            "gsm8k": 96.4,
            "elo_rating": 1272,
            "mt_bench": 9.4,
            "bigbench_hard": 87.2,
            "eq_bench": 90.8
        },
        "context_length": 200000,
        "provider": "Anthropic"
    },
    
    # Google Models - May 2025
    "gemini-1.5-pro": {
        "aliases": ["gemini-1.5-pro-latest", "gemini-pro-1.5"],
        "release_date": "2024-05",
        "benchmarks": {
            "mmlu": 85.9,
            "humaneval": 84.1,
            "arc_challenge": 95.2,
            "hellaswag": 94.4,
            "truthfulqa": 83.7,
            "gsm8k": 91.7,
            "elo_rating": 1228,
            "mt_bench": 8.9
        },
        "context_length": 2000000,
        "provider": "Google"
    },
    
    "gemini-1.5-flash": {
        "aliases": ["gemini-flash-1.5"],
        "release_date": "2024-05",
        "benchmarks": {
            "mmlu": 78.9,
            "humaneval": 74.3,
            "arc_challenge": 92.5,
            "hellaswag": 91.2,
            "truthfulqa": 80.4,
            "gsm8k": 86.2,
            "elo_rating": 1163,
            "mt_bench": 8.3
        },
        "context_length": 1000000,
        "provider": "Google"
    },
    
    # xAI Models - May 2025
    "grok-2": {
        "aliases": ["xai-grok-2"],
        "release_date": "2024-08",
        "benchmarks": {
            "mmlu": 87.5,
            "humaneval": 88.0,
            "arc_challenge": 95.4,
            "hellaswag": 94.8,
            "truthfulqa": 85.3,
            "gsm8k": 94.1,
            "elo_rating": 1254,
            "mt_bench": 9.0
        },
        "context_length": 128000,
        "provider": "xAI"
    },
    
    # Meta Models
    "llama-3.1-405b": {
        "aliases": ["meta-llama/Llama-3.1-405B-Instruct"],
        "release_date": "2024-07",
        "benchmarks": {
            "mmlu": 88.6,
            "humaneval": 89.0,
            "arc_challenge": 96.1,
            "hellaswag": 95.2,
            "truthfulqa": 84.8,
            "gsm8k": 95.1,
            "elo_rating": 1267,
            "mt_bench": 9.2
        },
        "context_length": 128000,
        "provider": "Meta"
    },
    
    "llama-3.1-70b": {
        "aliases": ["meta-llama/Llama-3.1-70B-Instruct"],
        "release_date": "2024-07",
        "benchmarks": {
            "mmlu": 83.6,
            "humaneval": 81.7,
            "arc_challenge": 94.8,
            "hellaswag": 93.8,
            "truthfulqa": 82.4,
            "gsm8k": 92.0,
            "elo_rating": 1213,
            "mt_bench": 8.7
        },
        "context_length": 128000,
        "provider": "Meta"
    },
    
    # Mistral Models
    "mistral-large-2": {
        "aliases": ["mistral-large-2407"],
        "release_date": "2024-07",
        "benchmarks": {
            "mmlu": 84.0,
            "humaneval": 84.4,
            "arc_challenge": 94.2,
            "hellaswag": 93.7,
            "truthfulqa": 83.5,
            "gsm8k": 91.2,
            "elo_rating": 1218,
            "mt_bench": 8.8
        },
        "context_length": 128000,
        "provider": "Mistral"
    },
    
    # Alibaba Models
    "qwen2.5-72b": {
        "aliases": ["Qwen/Qwen2.5-72B-Instruct"],
        "release_date": "2024-11",
        "benchmarks": {
            "mmlu": 86.1,
            "humaneval": 86.0,
            "arc_challenge": 94.9,
            "hellaswag": 94.2,
            "truthfulqa": 83.2,
            "gsm8k": 92.8,
            "elo_rating": 1238,
            "mt_bench": 8.8,
            "c_eval": 91.6
        },
        "context_length": 131072,
        "provider": "Alibaba"
    },
    
    # DeepSeek Models
    "deepseek-v3": {
        "aliases": ["deepseek-chat-v3"],
        "release_date": "2025-01",
        "benchmarks": {
            "mmlu": 87.8,
            "humaneval": 88.9,
            "arc_challenge": 95.7,
            "hellaswag": 94.9,
            "truthfulqa": 85.6,
            "gsm8k": 94.7,
            "elo_rating": 1262,
            "mt_bench": 9.1
        },
        "context_length": 128000,
        "provider": "DeepSeek"
    },
    
    "deepseek-coder-v2": {
        "aliases": ["deepseek-coder-v2-instruct"],
        "release_date": "2024-06",
        "benchmarks": {
            "mmlu": 79.2,
            "humaneval": 90.2,
            "mbpp": 89.4,
            "apps": 84.3,
            "arc_challenge": 92.3,
            "hellaswag": 91.5,
            "truthfulqa": 81.2,
            "gsm8k": 88.4,
            "elo_rating": 1203,
            "mt_bench": 8.5
        },
        "context_length": 128000,
        "provider": "DeepSeek"
    },
    
    # Cohere Models
    "command-r-plus": {
        "aliases": ["cohere-command-r-plus"],
        "release_date": "2024-04",
        "benchmarks": {
            "mmlu": 83.4,
            "humaneval": 81.5,
            "arc_challenge": 93.5,
            "hellaswag": 93.0,
            "truthfulqa": 82.1,
            "gsm8k": 90.2,
            "elo_rating": 1192,
            "mt_bench": 8.5
        },
        "context_length": 128000,
        "provider": "Cohere"
    },
    
    # Inflection AI
    "inflection-2.5": {
        "aliases": ["pi-2.5", "inflection-pi-2.5"],
        "release_date": "2024-03",
        "benchmarks": {
            "mmlu": 81.6,
            "humaneval": 78.3,
            "arc_challenge": 92.8,
            "hellaswag": 92.1,
            "truthfulqa": 81.0,
            "gsm8k": 87.5,
            "elo_rating": 1171,
            "mt_bench": 8.2
        },
        "context_length": 32000,
        "provider": "Inflection"
    }
}

# Domain-specific benchmark leaders (May 2025)
DOMAIN_LEADERS = {
    "medical": {
        "med-palm-3": {"medqa": 94.8, "medmcqa": 92.3, "pubmedqa": 89.7},
        "gpt-4o": {"medqa": 91.2, "medmcqa": 88.5, "pubmedqa": 86.3},
        "claude-3.5-sonnet": {"medqa": 90.7, "medmcqa": 87.9, "pubmedqa": 85.8}
    },
    "legal": {
        "o3": {"legalbench": 89.3, "bar_exam": 95.2},
        "claude-3.5-sonnet": {"legalbench": 87.8, "bar_exam": 93.7},
        "gpt-4o": {"legalbench": 85.4, "bar_exam": 91.8}
    },
    "finance": {
        "bloomberg-gpt-2": {"finqa": 91.5, "financial_sentiment": 94.2},
        "o3": {"finqa": 89.7, "financial_sentiment": 92.1},
        "gpt-4o": {"finqa": 88.3, "financial_sentiment": 91.8}
    },
    "code": {
        "o3": {"humaneval": 95.8, "mbpp": 94.2, "apps": 89.7, "swe_bench": 73.2},
        "claude-4-opus": {"humaneval": 94.1, "mbpp": 91.8, "apps": 88.3, "swe_bench": 72.5},
        "claude-4-sonnet": {"humaneval": 93.2, "mbpp": 90.5, "apps": 87.1, "swe_bench": 72.7},
        "claude-3.5-sonnet": {"humaneval": 91.7, "mbpp": 89.8, "apps": 85.3, "swe_bench": 69.2},
        "deepseek-coder-v2": {"humaneval": 90.2, "mbpp": 89.4, "apps": 84.3, "swe_bench": 67.8},
        "gpt-4o": {"humaneval": 90.2, "mbpp": 88.7, "apps": 83.5, "swe_bench": 66.1}
    },
    "multilingual": {
        "gpt-4o": {"multilingual_mmlu": 88.3, "xquad": 91.7},
        "claude-3.5-sonnet": {"multilingual_mmlu": 87.8, "xquad": 90.9},
        "qwen2.5-72b": {"multilingual_mmlu": 89.2, "xquad": 91.5}
    }
}

# Usage statistics (tokens served in billions) - May 2025
USAGE_STATS = {
    "gpt-4o-mini": 82.3,
    "claude-3-haiku": 67.2,
    "gpt-3.5-turbo": 45.8,
    "llama-3.1-70b": 41.3,
    "gemini-1.5-flash": 38.7,
    "claude-3.5-sonnet": 28.1,
    "mistral-large-2": 22.4,
    "grok-2": 19.3,
    "o3": 15.2,
    "qwen2.5-72b": 12.8
} 