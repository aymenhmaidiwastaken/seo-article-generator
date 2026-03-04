#!/usr/bin/env python3
"""
Export crawler articles to Booma website blog-posts.js format.

Reads checkpoint JSON or Excel files, converts markdown content to HTML,
and appends new blog post entries to the website's blog-posts.js file.

On re-run, removes previously script-added posts (after the EXPORT_MARKER)
and replaces them with fresh output.
"""

import argparse
import json
import math
import os
import random
import re
import sys
from datetime import date, timedelta


# Paths
ARTICLES_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKPOINTS_DIR = os.path.join(ARTICLES_DIR, "checkpoints")
BLOG_POSTS_FILE = r"C:\Users\aymen\Desktop\booma\src\content\blog-posts.js"

# Marker inserted before script-added posts so re-runs can find and replace them
EXPORT_MARKER = "// --- AUTO-EXPORTED ARTICLES (do not edit below this line) ---"

# Category mapping based on keywords — ordered from most specific to least specific
CATEGORY_MAP = [
    # Specific frameworks/platforms first
    (["react native", "reactnative"],
     ["React Native", "Mobile Apps"]),
    (["flutter", "dart"],
     ["Flutter", "Mobile Apps"]),
    (["swiftui", "xcode"],
     ["iOS Development", "Mobile Apps"]),
    (["kotlin"],
     ["Android Development", "Mobile Apps"]),
    # Specific topics
    (["machine learning", "deep learning", "artificial intelligence", "chatbot", "gpt"],
     ["AI Solutions", "Mobile Apps"]),
    (["app store optimization", "aso"],
     ["App Marketing", "Growth Strategy"]),
    (["cross-platform", "hybrid app", "pwa", "progressive web"],
     ["Mobile Apps", "Web Development"]),
    (["game development", "gaming", "unity", "unreal", "mobile game"],
     ["Mobile Games", "Game Development"]),
    (["user experience", "user interface", "ux design", "ui design"],
     ["UX Design", "Mobile Apps"]),
    (["startup", "mvp", "funding", "entrepreneur"],
     ["Startup Tips", "Mobile Apps"]),
    (["authentication", "encryption", "cybersecurity", "oauth"],
     ["Mobile Apps", "Security"]),
    (["firebase", "backend", "aws", "database"],
     ["Mobile Apps", "Backend"]),
    # Platform keywords (broader)
    (["ios app", "iphone app", "ipad app", "swift"],
     ["iOS Development", "Mobile Apps"]),
    (["android app", "google play"],
     ["Android Development", "Mobile Apps"]),
    # Broad topics last
    (["marketing", "seo", "growth", "monetization", "revenue"],
     ["App Marketing", "Growth Strategy"]),
    (["testing", "qa", "quality assurance", "debug"],
     ["Mobile Apps", "Quality Assurance"]),
    (["security", "privacy", "data protection"],
     ["Mobile Apps", "Security"]),
    (["mobile app development", "app development", "mobile development"],
     ["Mobile Apps", "App Development"]),
    (["mobile app", "mobile application"],
     ["Mobile Apps", "Industry Trends"]),
]

# Fallback category
DEFAULT_CATEGORIES = ["Mobile Apps", "Industry Trends"]


def find_latest_checkpoint():
    """Find the most recent checkpoint JSON file."""
    if not os.path.isdir(CHECKPOINTS_DIR):
        return None
    json_files = [
        os.path.join(CHECKPOINTS_DIR, f)
        for f in os.listdir(CHECKPOINTS_DIR)
        if f.endswith(".json")
    ]
    if not json_files:
        return None
    return max(json_files, key=os.path.getmtime)


def load_articles_from_json(filepath):
    """Load articles from a checkpoint JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("articles", [])


def load_articles_from_excel(filepath):
    """Load articles from an Excel file."""
    try:
        import openpyxl
    except ImportError:
        print("Error: openpyxl is required to read Excel files.")
        print("Install it with: pip install openpyxl")
        sys.exit(1)

    wb = openpyxl.load_workbook(filepath, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    # Normalize headers: lowercase and replace spaces with underscores
    headers = []
    for h in rows[0]:
        if h:
            normalized = str(h).strip().lower().replace(" ", "_")
            headers.append(normalized)
        else:
            headers.append("")

    articles = []
    for row in rows[1:]:
        article = {}
        for i, header in enumerate(headers):
            if i < len(row):
                article[header] = row[i]
        articles.append(article)
    wb.close()
    return articles


def get_all_slugs(blog_posts_content):
    """Extract ALL slugs from blog-posts.js (original + previously exported)."""
    return set(re.findall(r'slug:\s*"([^"]+)"', blog_posts_content))


def clean_title(title):
    """Clean trailing **, quotes, and whitespace from title."""
    if not title:
        return "Untitled"
    title = title.strip()
    title = re.sub(r'\*+\s*$', '', title)
    title = title.strip('"\'')
    return title.strip()


def fix_year_references(text):
    """Replace 2025 references with 2026."""
    if not text:
        return text
    text = text.replace("2025", "2026")
    return text


def generate_date_2026():
    """Generate a random date in 2026 (Jan 1 - Feb 5)."""
    start = date(2026, 1, 1)
    end = date(2026, 2, 5)
    delta = (end - start).days
    random_days = random.randint(0, delta)
    return (start + timedelta(days=random_days)).isoformat()


def normalize_date(article_date):
    """Ensure date is in 2026. Old dates get a random 2026 date."""
    if not article_date or article_date == "None":
        return generate_date_2026()
    try:
        year = int(article_date[:4])
        if year < 2026:
            return generate_date_2026()
        return article_date
    except (ValueError, IndexError):
        return generate_date_2026()


def truncate_text(text, max_len=160):
    """Truncate text to max_len characters, ending at a word boundary."""
    if not text or len(text) <= max_len:
        return text or ""
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > max_len - 40:
        truncated = truncated[:last_space]
    return truncated.rstrip(".,;:- ") + "..."


def escape_js_template(text):
    """Escape backticks and ${...} for JavaScript template literals."""
    text = text.replace("\\", "\\\\")
    text = text.replace("`", "\\`")
    text = text.replace("${", "\\${")
    return text


def markdown_to_html(md_text):
    """Convert markdown-style text to HTML matching the blog template format."""
    if not md_text:
        return ""

    lines = md_text.split("\n")
    html_parts = []
    section_counter = 0
    i = 0
    in_list = None  # 'ul' or 'ol'

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            if in_list:
                html_parts.append(f"      </{in_list}>")
                in_list = None
            i += 1
            continue

        # Heading: ## or ###
        heading_match = re.match(r'^(#{2,3})\s+(.+)$', stripped)
        if heading_match:
            if in_list:
                html_parts.append(f"      </{in_list}>")
                in_list = None
            section_counter += 1
            heading_text = heading_match.group(2).strip()
            heading_text = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', heading_text)
            html_parts.append(f'      <h2 id="section-{section_counter}">{heading_text}</h2>')
            i += 1
            continue

        # Standalone bold line (acts as heading): **Some Text**
        bold_line_match = re.match(r'^\*\*(.+?)\*\*\s*$', stripped)
        if bold_line_match:
            if in_list:
                html_parts.append(f"      </{in_list}>")
                in_list = None
            section_counter += 1
            heading_text = bold_line_match.group(1).strip()
            html_parts.append(f'      <h2 id="section-{section_counter}">{heading_text}</h2>')
            i += 1
            continue

        # Blockquote: > text
        if stripped.startswith("> "):
            if in_list:
                html_parts.append(f"      </{in_list}>")
                in_list = None
            quote_text = stripped[2:].strip()
            quote_text = convert_inline_markdown(quote_text)
            html_parts.append(f"      <blockquote>{quote_text}</blockquote>")
            i += 1
            continue

        # Unordered list item: - item or * item
        ul_match = re.match(r'^[\-\*]\s+(.+)$', stripped)
        if ul_match:
            if in_list and in_list != "ul":
                html_parts.append(f"      </{in_list}>")
                in_list = None
            if not in_list:
                html_parts.append("      <ul>")
                in_list = "ul"
            item_text = convert_inline_markdown(ul_match.group(1).strip())
            html_parts.append(f"        <li>{item_text}</li>")
            i += 1
            continue

        # Ordered list item: 1. item
        ol_match = re.match(r'^\d+\.\s+(.+)$', stripped)
        if ol_match:
            if in_list and in_list != "ol":
                html_parts.append(f"      </{in_list}>")
                in_list = None
            if not in_list:
                html_parts.append("      <ol>")
                in_list = "ol"
            item_text = convert_inline_markdown(ol_match.group(1).strip())
            html_parts.append(f"        <li>{item_text}</li>")
            i += 1
            continue

        # Regular paragraph
        if in_list:
            html_parts.append(f"      </{in_list}>")
            in_list = None
        para_text = convert_inline_markdown(stripped)
        html_parts.append(f"      <p>{para_text}</p>")
        i += 1

    if in_list:
        html_parts.append(f"      </{in_list}>")

    return "\n".join(html_parts)


def convert_inline_markdown(text):
    """Convert inline markdown (bold, italic) to HTML."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


def extract_headings(md_text):
    """Extract h2 heading texts from markdown content for tableOfContents."""
    if not md_text:
        return []
    headings = []
    for line in md_text.split("\n"):
        stripped = line.strip()
        h_match = re.match(r'^#{2,3}\s+(.+)$', stripped)
        if h_match:
            heading = h_match.group(1).strip()
            heading = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', heading)
            headings.append(heading)
            continue
        bold_match = re.match(r'^\*\*(.+?)\*\*\s*$', stripped)
        if bold_match:
            headings.append(bold_match.group(1).strip())
    return headings


def calculate_read_time(content):
    """Calculate read time in minutes based on word count (200 wpm)."""
    if not content:
        return 3
    word_count = len(content.split())
    return max(1, math.ceil(word_count / 200))


def format_keywords_string(keywords_found):
    """Format keywords list into a comma-separated string."""
    if isinstance(keywords_found, list):
        return ", ".join(keywords_found)
    if isinstance(keywords_found, str):
        return keywords_found
    return ""


def format_tags(keywords_found):
    """Get first 5 keywords as title-cased tags."""
    if isinstance(keywords_found, str):
        keywords_found = [k.strip() for k in keywords_found.split(",")]
    if not isinstance(keywords_found, list):
        return []
    tags = []
    for kw in keywords_found[:5]:
        if kw:
            tags.append(kw.strip().title())
    return tags


def infer_categories(article):
    """Infer categories from keywords, slug, and title instead of using raw 'Technology'."""
    searchable = ""
    kw = article.get("keywords_found", [])
    if isinstance(kw, list):
        searchable += " ".join(kw).lower() + " "
    elif isinstance(kw, str):
        searchable += kw.lower() + " "
    searchable += (article.get("slug", "") + " ").replace("-", " ")
    searchable += (article.get("rewritten_title", "") or "").lower() + " "

    for keyword_list, categories in CATEGORY_MAP:
        for keyword in keyword_list:
            # Use word boundary matching to avoid "game" matching "game-changer"
            if re.search(r'\b' + re.escape(keyword) + r'\b', searchable):
                return categories

    return DEFAULT_CATEGORIES


def generate_cover_image(slug):
    """Generate a cover image path from the slug, like existing articles do."""
    # Take the slug, shorten it if very long, and use as image filename
    # e.g. "mastering-mobile-app-development-guide" -> "mastering-mobile-app-development-guide.jpg"
    parts = slug.split("-")
    # Keep max 5-6 meaningful words for the filename
    if len(parts) > 6:
        parts = parts[:6]
    image_name = "-".join(parts)
    return f"/assets/images/blog/{image_name}.jpg"


def escape_js_string(s):
    """Escape a string for use in a JS double-quoted string."""
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    return s


def format_blog_post_js(article, post_number):
    """Format a single article as a JavaScript blog post object."""
    title = clean_title(article.get("rewritten_title", ""))
    title = fix_year_references(title)
    slug = article.get("slug", "")
    meta_desc = article.get("meta_description", "") or ""
    meta_desc = fix_year_references(meta_desc)
    excerpt = truncate_text(meta_desc, 160)
    meta_description = truncate_text(meta_desc, 160)
    keywords_found = article.get("keywords_found", [])
    keywords_str = format_keywords_string(keywords_found)
    article_date = normalize_date(article.get("date_published", "") or article.get("date", ""))
    categories = infer_categories(article)
    rewritten_content = article.get("rewritten_content", "")
    rewritten_content = fix_year_references(rewritten_content)
    read_time = calculate_read_time(rewritten_content)
    tags = format_tags(keywords_found)
    headings = extract_headings(rewritten_content)
    html_content = markdown_to_html(rewritten_content)
    html_content_escaped = escape_js_template(html_content)

    cover_image = generate_cover_image(slug)
    cover_image_alt = "-".join(slug.split("-")[:6])

    # Build tableOfContents array
    toc_items = ",\n".join(f'      "{escape_js_string(h)}"' for h in headings)
    toc_block = f"[\n{toc_items}\n    ]" if headings else "[]"

    # Build tags array
    tags_items = ", ".join(f'"{escape_js_string(t)}"' for t in tags)
    tags_block = f"[{tags_items}]"

    # Build categories array
    cat_items = ", ".join(f'"{escape_js_string(c)}"' for c in categories)
    categories_block = f"[{cat_items}]"

    js = f"""  // Post {post_number}
  {{
    slug: "{escape_js_string(slug)}",
    title: "{escape_js_string(title)}",
    excerpt: "{escape_js_string(excerpt)}",
    metaDescription: "{escape_js_string(meta_description)}",
    keywords: "{escape_js_string(keywords_str)}",
    date: "{escape_js_string(article_date)}",
    readTime: {read_time},
    categories: {categories_block},
    tags: {tags_block},
    coverImage: "{cover_image}",
    coverImageAlt: "{escape_js_string(cover_image_alt)}",
    tableOfContents: {toc_block},
    content: `
{html_content_escaped}
`
  }}"""
    return js


def main():
    parser = argparse.ArgumentParser(
        description="Export crawler articles to Booma blog-posts.js"
    )
    parser.add_argument(
        "--input",
        nargs="+",
        help="Path(s) to checkpoint JSON or Excel files (default: latest checkpoint)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of articles to export (0 = all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview output without writing to blog-posts.js",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace all previously exported articles instead of appending",
    )
    args = parser.parse_args()

    # Determine input files
    input_files = args.input
    if not input_files:
        latest = find_latest_checkpoint()
        if not latest:
            print("Error: No checkpoint files found in checkpoints/ directory.")
            print("Use --input to specify a file.")
            sys.exit(1)
        input_files = [latest]

    # Load articles from all input files
    articles = []
    for input_file in input_files:
        if not os.path.isfile(input_file):
            print(f"Warning: File not found, skipping: {input_file}")
            continue
        print(f"Reading: {input_file}")
        if input_file.endswith(".xlsx"):
            file_articles = load_articles_from_excel(input_file)
        elif input_file.endswith(".json"):
            file_articles = load_articles_from_json(input_file)
        else:
            print(f"Warning: Unsupported format, skipping: {input_file}")
            continue
        print(f"  -> {len(file_articles)} articles")
        articles.extend(file_articles)

    print(f"Total articles loaded: {len(articles)}")

    # Filter completed articles
    completed = [
        a for a in articles
        if str(a.get("rewrite_status", "")).lower() == "completed"
        and a.get("rewritten_content")
        and a.get("slug")
    ]
    print(f"Completed articles with content: {len(completed)}")

    # Read existing blog-posts.js
    if not os.path.isfile(BLOG_POSTS_FILE):
        print(f"Error: Blog posts file not found: {BLOG_POSTS_FILE}")
        sys.exit(1)

    with open(BLOG_POSTS_FILE, "r", encoding="utf-8") as f:
        existing_content = f.read()

    # Determine base content depending on mode
    marker_pos = existing_content.find(EXPORT_MARKER)

    if args.replace:
        # --replace: strip everything after marker (or after original posts)
        if marker_pos != -1:
            base_content = existing_content[:marker_pos].rstrip()
            print("Replace mode: removing all previously exported articles.")
        else:
            closing_pos = existing_content.rfind("];")
            if closing_pos == -1:
                print("Error: Could not find closing ]; in blog-posts.js")
                sys.exit(1)
            base_content = existing_content[:closing_pos].rstrip()
        if base_content.endswith(","):
            base_content = base_content[:-1].rstrip()
    else:
        # Default: append mode — keep everything, add after last post
        closing_pos = existing_content.rfind("];")
        if closing_pos == -1:
            print("Error: Could not find closing ]; in blog-posts.js")
            sys.exit(1)
        base_content = existing_content[:closing_pos].rstrip()
        if base_content.endswith(","):
            base_content = base_content[:-1].rstrip()
        # Remove the old marker line if it exists (we'll re-add it)
        # Keep the exported posts, just strip the ];
        if marker_pos != -1:
            print("Append mode: keeping previously exported articles, adding new ones.")
        else:
            print("First export: adding articles.")

    # Deduplicate against ALL slugs currently in the file
    existing_slugs = get_all_slugs(existing_content)
    print(f"Existing blog posts (total): {len(existing_slugs)}")

    # Filter out duplicates (against original posts AND within the batch)
    seen_slugs = set(existing_slugs)
    new_articles = []
    for a in completed:
        slug = a.get("slug")
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            new_articles.append(a)
    print(f"New unique articles to add: {len(new_articles)}")

    if not new_articles:
        print("No new articles to add. All slugs already exist in original posts.")
        return

    # Apply limit
    if args.limit > 0:
        new_articles = new_articles[: args.limit]
        print(f"Limited to: {len(new_articles)} articles")

    # Determine starting post number from base content
    existing_post_numbers = re.findall(r'// Post (\d+)', base_content)
    if existing_post_numbers:
        start_number = max(int(n) for n in existing_post_numbers) + 1
    else:
        start_number = 1

    # Use fixed seed for reproducible dates across runs
    random.seed(42)

    # Generate JS for each article
    js_entries = []
    for i, article in enumerate(new_articles):
        post_num = start_number + i
        js_entry = format_blog_post_js(article, post_num)
        js_entries.append(js_entry)

    new_js_block = ",\n".join(js_entries)

    if args.dry_run:
        print("\n--- DRY RUN: Preview of generated JavaScript ---\n")
        preview_entries = js_entries[:3]
        print(",\n".join(preview_entries))
        if len(js_entries) > 3:
            print(f"\n... and {len(js_entries) - 3} more entries ...")
        print(f"\n--- Total: {len(js_entries)} new blog posts would be added ---")
        return

    # Build final file
    # If base_content already has the marker, don't add another one
    if EXPORT_MARKER in base_content:
        updated_content = base_content + ",\n" + new_js_block + "\n];\n"
    else:
        updated_content = (
            base_content
            + ",\n"
            + EXPORT_MARKER
            + "\n"
            + new_js_block
            + "\n];\n"
        )

    with open(BLOG_POSTS_FILE, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print(f"\nSuccessfully added {len(js_entries)} blog posts to {BLOG_POSTS_FILE}")
    print(f"Post numbers: {start_number} to {start_number + len(js_entries) - 1}")
    print(f"\nNext steps:")
    print(f"  cd C:\\Users\\aymen\\Desktop\\booma")
    print(f"  npm run build")


if __name__ == "__main__":
    main()
