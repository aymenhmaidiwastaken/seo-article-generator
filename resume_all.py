"""Resume all 10 crawl jobs in batches of 3."""

import subprocess
import sys
import time

BATCH_SIZE = 3

JOBS = [
    {
        "name": "dating_couples",
        "keywords": [
            "dating tips", "dating advice", "relationship advice", "couples tips",
            "love advice", "first date tips", "online dating", "dating app tips",
            "healthy relationships", "marriage advice", "couples communication",
            "relationship goals", "dating for beginners", "long distance relationship",
            "couple activities", "romantic date ideas", "relationship problems",
            "dating red flags", "how to find love", "couples therapy",
        ],
        "output": "dating_couples.xlsx",
    },
    {
        "name": "dating_couples_2",
        "keywords": [
            "relationship tips", "love life", "dating mistakes", "couple goals",
            "romantic relationships", "dating in your 30s", "dating in your 40s",
            "single life", "finding a partner", "commitment issues",
            "trust in relationships", "dating after divorce", "wedding planning",
            "engagement tips", "honeymoon ideas", "anniversary ideas",
            "couples vacation", "date night ideas", "flirting tips", "how to be romantic",
        ],
        "output": "dating_couples_2.xlsx",
    },
    {
        "name": "mobile_games",
        "keywords": [
            "mobile game development", "mobile gaming tips", "best mobile games",
            "mobile game design", "unity mobile games", "mobile game monetization",
            "casual mobile games", "mobile game marketing", "hyper casual games",
            "mobile rpg games", "mobile puzzle games", "mobile game trends",
            "android game development", "ios game development", "mobile esports",
            "mobile game analytics", "game app development", "mobile multiplayer games",
            "free to play mobile games", "mobile game revenue",
        ],
        "output": "mobile_games.xlsx",
    },
    {
        "name": "mobile_marketing",
        "keywords": [
            "mobile marketing", "app store optimization", "mobile advertising",
            "mobile user acquisition", "app marketing strategy", "mobile app promotion",
            "aso tips", "app store ranking", "mobile ad networks",
            "push notification marketing", "mobile engagement", "app retention strategies",
            "mobile analytics", "in-app advertising", "mobile conversion optimization",
            "app install campaigns", "mobile growth hacking", "app store keywords",
            "mobile attribution", "mobile remarketing",
        ],
        "output": "mobile_marketing.xlsx",
    },
    {
        "name": "mobile_apps",
        "keywords": [
            "mobile app development", "app development tips", "react native development",
            "flutter app development", "ios app development", "android app development",
            "mobile app design", "app ui ux design", "mobile app testing",
            "app development cost", "mobile app features", "app development trends",
            "cross platform development", "mobile app security",
            "app performance optimization", "mobile backend development",
            "app development tools", "mobile app monetization", "saas mobile apps",
            "enterprise mobile apps",
        ],
        "output": "mobile_apps.xlsx",
    },
    {
        "name": "mobile_apps_frameworks",
        "keywords": [
            "swift app development", "kotlin app development", "xamarin development",
            "ionic framework", "cordova mobile apps", "native app development",
            "hybrid app development", "progressive web apps", "pwa development",
            "mobile sdk", "app development frameworks", "mobile devops",
            "app debugging tools", "mobile ci cd", "app prototyping tools",
            "figma mobile design", "sketch app design", "mobile wireframing",
            "app mockup design", "xcode development",
        ],
        "output": "mobile_apps_frameworks.xlsx",
    },
    {
        "name": "mobile_apps_business",
        "keywords": [
            "app startup ideas", "mobile app business", "app revenue models",
            "app subscription model", "freemium app strategy", "app business plan",
            "mobile app investment", "app development company", "hire app developers",
            "app outsourcing", "app mvp development", "lean app development",
            "app launch strategy", "app pitch deck", "mobile app funding",
            "app startup funding", "app business model", "white label apps",
            "app reskinning", "mobile saas business",
        ],
        "output": "mobile_apps_business.xlsx",
    },
    {
        "name": "mobile_apps_features",
        "keywords": [
            "app push notifications", "in app purchases", "app authentication",
            "mobile payment integration", "app social login", "app geolocation features",
            "mobile camera integration", "app chat features", "real time app features",
            "offline app functionality", "app cloud sync", "mobile biometric login",
            "app voice recognition", "augmented reality apps", "ar mobile apps",
            "vr mobile apps", "machine learning mobile apps", "ai chatbot apps",
            "app personalization", "mobile app api integration",
        ],
        "output": "mobile_apps_features.xlsx",
    },
    {
        "name": "mobile_apps_industries",
        "keywords": [
            "fitness app development", "health app development", "fintech app development",
            "ecommerce mobile app", "food delivery app", "taxi app development",
            "social media app development", "education app development",
            "travel app development", "real estate app", "healthcare mobile app",
            "telemedicine app", "banking app development", "insurance app development",
            "entertainment app development", "music streaming app",
            "video streaming app", "news app development", "sports app development",
            "dating app development",
        ],
        "output": "mobile_apps_industries.xlsx",
    },
    {
        "name": "mobile_apps_quality",
        "keywords": [
            "app user experience", "mobile app usability", "app accessibility",
            "app load time optimization", "mobile app crashes", "app bug fixing",
            "app quality assurance", "mobile app testing tools", "app beta testing",
            "app user feedback", "app store reviews", "app rating optimization",
            "mobile app onboarding", "app user retention", "app engagement metrics",
            "mobile app kpis", "app session length", "app churn rate",
            "mobile app benchmarks", "app competitor analysis",
        ],
        "output": "mobile_apps_quality.xlsx",
    },
]


def build_command(job):
    cmd = [sys.executable, "run.py"]
    for kw in job["keywords"]:
        cmd.append(kw)
    cmd += ["--resume", "--output", job["output"], "--target", "15000",
            "--min-words", "200", "--min-relevance", "0.05"]
    return cmd


def run_batch(batch, batch_num, total_batches):
    print(f"\n{'='*60}")
    print(f"  BATCH {batch_num}/{total_batches} - Starting {len(batch)} jobs")
    print(f"{'='*60}")
    for job in batch:
        print(f"  -> {job['name']} ({job['output']})")
    print()

    processes = []
    for job in batch:
        cmd = build_command(job)
        log_file = open(f"{job['name']}_log.txt", "w", encoding="utf-8")
        proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
        processes.append((job, proc, log_file))
        print(f"  [STARTED] {job['name']} (PID: {proc.pid})")

    print(f"\n  Waiting for batch {batch_num} to finish...\n")

    results = []
    for job, proc, log_file in processes:
        proc.wait()
        log_file.close()
        status = "OK" if proc.returncode == 0 else f"FAILED (code {proc.returncode})"
        results.append((job["name"], status))
        print(f"  [DONE] {job['name']} - {status}")

    return results


def main():
    print("=" * 60)
    print("  BATCH RESUME SCRIPT")
    print(f"  {len(JOBS)} jobs, {BATCH_SIZE} at a time")
    print("=" * 60)

    all_results = []
    batches = [JOBS[i:i + BATCH_SIZE] for i in range(0, len(JOBS), BATCH_SIZE)]

    start = time.time()
    for i, batch in enumerate(batches, 1):
        batch_start = time.time()
        results = run_batch(batch, i, len(batches))
        all_results.extend(results)
        elapsed = time.time() - batch_start
        print(f"\n  Batch {i} completed in {elapsed/60:.1f} minutes")

    total = time.time() - start
    print(f"\n{'='*60}")
    print("  ALL BATCHES COMPLETE")
    print(f"  Total time: {total/3600:.1f} hours")
    print(f"{'='*60}")
    for name, status in all_results:
        print(f"  {name}: {status}")
    print()


if __name__ == "__main__":
    main()
