<p align="center">
  <h1 align="center">SEO Article Generator</h1>
  <p align="center">
    <strong>The most powerful open-source AI-powered SEO article generation pipeline.</strong>
  </p>
  <p align="center">
    Crawl thousands of articles from 5 search engines, extract clean content, and rewrite them into unique SEO-optimized articles using local AI — all from a single command.
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> &bull;
    <a href="#features">Features</a> &bull;
    <a href="#how-it-works">How It Works</a> &bull;
    <a href="#usage">Usage</a> &bull;
    <a href="#configuration">Configuration</a>
  </p>
</p>

---

## Why SEO Article Generator?

Most SEO content tools are expensive SaaS products with monthly fees, word limits, and vendor lock-in. **SEO Article Generator** is a free, open-source alternative that runs entirely on your machine using local AI models via [Ollama](https://ollama.ai). No API keys. No usage limits. No recurring costs.

- **Scale**: Generate hundreds or thousands of unique articles in a single run
- **Quality**: AI-rewritten content with natural keyword placement, proper headings, and SEO metadata
- **Privacy**: Everything runs locally — your content never leaves your machine
- **Resilient**: Built-in checkpoint system lets you pause and resume at any time
- **Flexible**: Works with any niche or topic, any Ollama-compatible model

---

## Features

### Multi-Engine Search Aggregation
Searches **5 engines simultaneously** — DuckDuckGo, Bing, Google, Reddit, and Quora — with 25 query variations per keyword for maximum coverage. Automatic deduplication ensures no duplicate sources.

### Intelligent Content Extraction
Uses [trafilatura](https://github.com/adbar/trafilatura) for state-of-the-art content extraction. Automatically strips navigation, ads, and boilerplate. Filters out junk content (Reddit drama, app store listings, etc.) with regex-based detection.

### AI-Powered SEO Rewriting
Rewrites every article using a local LLM through Ollama. Each article gets:
- Completely rephrased content (unique enough to pass plagiarism checks)
- Natural keyword placement (3-5 mentions per article)
- SEO-optimized title and meta description
- Proper heading structure (`##` headings)
- URL-friendly slug
- Auto-categorization

### Relevance Scoring & Filtering
Every extracted article is scored for relevance against your target keywords. Configurable thresholds let you control quality vs. quantity. Content is also filtered by minimum word count and deduplicated by title and content fingerprinting.

### Checkpoint & Resume System
Long crawls are protected by automatic checkpoints saved every N articles. If your machine crashes, your internet drops, or you just need to stop — run with `--resume` to pick up exactly where you left off. No work is ever lost.

### Batch Processing
Run 10+ keyword campaigns simultaneously with the batch runner. Processes jobs in parallel batches with per-job logging and comprehensive status reporting.

### Excel Export with Formatting
Exports to professionally formatted `.xlsx` files with:
- Frozen header rows and auto-filters
- Color-coded rewrite status (green/yellow/red)
- Summary sheet with statistics, top sources, and category breakdown
- 15 data columns including original and rewritten content

### Blog Integration
Built-in exporter converts articles to JavaScript blog post objects with HTML content, table of contents, reading time, categories, and tags — ready to drop into any static site or CMS.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    SEO Article Generator                     │
├──────────┬──────────┬──────────────┬──────────┬─────────────┤
│  SEARCH  │ EXTRACT  │   FILTER     │ REWRITE  │   EXPORT    │
│          │          │              │          │             │
│ DuckDuck │ Fetch    │ Word count   │ Ollama   │ Excel       │
│ Bing     │ HTML     │ Relevance    │ LLM      │ Blog JS     │
│ Google   │ Clean    │ Dedup        │ SEO      │ Stats       │
│ Reddit   │ Content  │ Junk filter  │ Meta     │ Summary     │
│ Quora    │ Metadata │ Domain block │ Slug     │             │
└──────────┴──────────┴──────────────┴──────────┴─────────────┘
     │           │            │            │           │
     ▼           ▼            ▼            ▼           ▼
  5 engines   trafilatura  Smart       Local AI    Formatted
  25 queries  extraction   filtering   rewriting   .xlsx output
  per keyword              pipeline    via Ollama
```

---

## Quick Start

### Prerequisites

- **Python 3.8+**
- **[Ollama](https://ollama.ai)** installed and running (for AI rewriting)

### Installation

```bash
# Clone the repository
git clone https://github.com/aymenhmaidiwastaken/seo-article-generator.git
cd seo-article-generator

# Install dependencies
pip install -r requirements.txt

# Pull an AI model (llama3 recommended)
ollama pull llama3
```

### Generate Your First Articles

```bash
# Generate articles about any topic
python -m article_crawler "keto diet" "keto recipes" "ketogenic lifestyle"
```

That's it. The tool will search the web, extract articles, rewrite them with AI, and export everything to `articles_output.xlsx`.

---

## Usage

### Basic Usage

```bash
# Single keyword
python -m article_crawler "mobile app development"

# Multiple keywords for broader coverage
python -m article_crawler "react native" "flutter" "cross platform apps"

# Custom output file and target count
python -m article_crawler "machine learning" -o ml_articles.xlsx -t 500
```

### Advanced Usage

```bash
# Crawl without AI rewriting (just collect raw articles)
python -m article_crawler "python programming" --no-rewrite

# Resume an interrupted crawl
python -m article_crawler "python programming" --resume

# Rewrite articles from an existing Excel file
python -m article_crawler --rewrite-only raw_articles.xlsx -o rewritten.xlsx

# Use specific search engines only
python -m article_crawler "web3" --engines duckduckgo bing

# Use a different AI model
python -m article_crawler "fitness tips" --model mistral

# Fine-tune extraction filters
python -m article_crawler "seo tips" --min-words 200 --min-relevance 0.05

# Verbose logging for debugging
python -m article_crawler "blockchain" -v
```

### Batch Processing

For large-scale content generation across multiple topics:

```bash
# Edit resume_all.py with your keyword campaigns, then:
python resume_all.py
```

This processes multiple keyword sets in parallel batches with automatic logging.

### Blog Export

Convert generated articles to blog-ready JavaScript:

```bash
python export_to_blog.py --input articles_output.xlsx --limit 100
```

---

## Configuration

### CLI Options

| Option | Default | Description |
|---|---|---|
| `keywords` | (required) | Search keywords/phrases |
| `-o, --output` | `articles_output.xlsx` | Output Excel file path |
| `-t, --target` | `5000` | Target number of articles |
| `--min-words` | `300` | Minimum article word count |
| `--min-relevance` | `0.1` | Relevance score threshold (0-1) |
| `--engines` | `duckduckgo bing reddit quora` | Search engines to use |
| `--model` | `llama3` | Ollama model for rewriting |
| `--ollama-url` | `http://localhost:11434` | Ollama server URL |
| `--resume` | `false` | Resume from checkpoint |
| `--no-rewrite` | `false` | Skip AI rewriting phase |
| `--rewrite-only` | — | Rewrite existing Excel file |
| `--skip-dedup` | `false` | Allow duplicate articles |
| `--checkpoint-every` | `25` | Save progress every N articles |
| `-v, --verbose` | `false` | Enable debug logging |

### Supported Search Engines

| Engine | Method | Reliability | Notes |
|---|---|---|---|
| DuckDuckGo | API (`ddgs`) | High | Most reliable, recommended |
| Bing | Web scraping | High | Good complement to DDG |
| Google | Web scraping | Low | Frequently rate-limited |
| Reddit | JSON API | Medium | Finds articles shared on Reddit |
| Quora | DDG site search | Medium | Q&A content via DuckDuckGo |

### Supported AI Models

Any model available through Ollama works. Recommended:

| Model | Speed | Quality | Best For |
|---|---|---|---|
| `llama3` | Fast | High | General-purpose rewriting |
| `llama3:70b` | Slow | Very High | Premium quality output |
| `mistral` | Fast | Good | Quick drafts |
| `mixtral` | Medium | High | Balanced speed/quality |
| `gemma2` | Fast | Good | Lightweight rewriting |

---

## Project Structure

```
seo-article-generator/
├── article_crawler/          # Core package
│   ├── __init__.py           # Package metadata
│   ├── __main__.py           # Module entry point
│   ├── main.py               # CLI & orchestrator
│   ├── searcher.py           # Multi-engine search (5 engines)
│   ├── extractor.py          # Content extraction & filtering
│   ├── rewriter.py           # AI rewriting via Ollama
│   ├── exporter.py           # Excel export with formatting
│   ├── checkpoint.py         # Save/resume system
│   └── utils.py              # Helpers (delays, slugs, URL filtering)
├── run.py                    # Convenience wrapper
├── resume_all.py             # Batch job runner
├── export_to_blog.py         # Blog CMS exporter
├── requirements.txt          # Python dependencies
└── README.md
```

---

## Output Format

The generated Excel file contains 15 columns:

| Column | Description |
|---|---|
| Title | Original article title (cleaned) |
| Article Content | Original extracted content |
| Source URL | Where the article was found |
| Date Published | Publication date |
| Author | Article author |
| Word Count | Number of words |
| Meta Description | SEO meta description |
| Keywords Found | Matching target keywords |
| Headings | H1-H3 heading structure |
| Source Domain | Website domain |
| Rewritten Title | AI-generated SEO title |
| Rewritten Content | Fully rewritten article |
| Rewrite Status | completed / pending / failed |
| Slug | URL-friendly slug |
| Category | Auto-assigned category |

A **Summary** sheet is also generated with statistics, top source domains, and category distribution.

---

## Tips for Best Results

1. **Use 3-5 specific keywords** per run for focused, high-relevance articles
2. **Start with `--no-rewrite`** to preview what gets collected before spending time on AI rewriting
3. **Use `--resume`** liberally — the checkpoint system makes it safe to stop and restart anytime
4. **Lower `--min-relevance`** to `0.05` if you want more articles (at the cost of some off-topic results)
5. **Use `llama3:70b`** for the highest quality rewrites if you have the hardware
6. **Run batch jobs overnight** using `resume_all.py` for large-scale content generation

---

## Contributing

Contributions are welcome! Some ideas for improvement:

- Add more search engines (Yandex, Brave Search, etc.)
- Support cloud LLM APIs (OpenAI, Anthropic, etc.) as rewriting backends
- Add Markdown/HTML export formats
- Implement content spinning with synonym replacement
- Add image extraction and AI image generation
- Build a web UI dashboard for monitoring crawl progress
- WordPress/Ghost/Hugo direct publishing integration

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <sub>Built for content creators, SEO professionals, and developers who believe great tools should be free and open.</sub>
</p>
