import ago
import datetime

from flask import (
    Flask,
    request,
    render_template,
)

from . import (
    serpapi,
    domains,
    sitemaps,
)


import asyncio
import platform
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


app = Flask(__name__)


@app.route("/")
def home():
    return render_template(
        'home.html',
    )


@app.route("/serp-finder")
def serp_finder():
    query = request.args.get('query')

    if not query:
        return render_template(
            'serp_finder.html',
        )

    serp_results = serpapi.search(query, 100)
    domain_results = serpapi.extract_domains_from_results(serp_results)

    report = []
    for i in range(len(domain_results)):
        report.append({
            'serp': serp_results[i],
            'domain': domain_results[i],
        })

    return render_template(
        'serp_finder.html',
        report=report,
    )


@app.route("/check-domain")
def check_domain():
    domain = request.args.get('domain')
    if not domain:
        return {
            "error": "No domain specified",
        }

    creation_date = domains.get_domain_creation_date(domain)

    result = {
        'creation_date': creation_date,
    }
    if isinstance(creation_date, datetime.datetime):
        humanized = ago.human(creation_date)
        result['humanized'] = humanized
        result['creation_date'] = creation_date.date().isoformat()

        today = datetime.date.today()
        year_age = today.year - creation_date.year
        if today.month < creation_date.month and today.day < creation_date.day:
            year_age -= 1

        result['year_age'] = year_age

    return result


@app.route("/sitemap-analyzer")
def sitemap_analyzer():
    query = request.args.get('query')

    if not query:
        return render_template(
            'sitemap_analyzer.html',
        )

    serp_results = serpapi.search(query, 30)
    domain_results = serpapi.extract_domains_from_results(serp_results)

    report = []
    for i in range(len(domain_results)):
        report.append({
            'serp': serp_results[i],
            'domain': domain_results[i],
        })

    return render_template(
        'sitemap_analyzer.html',
        report=report,
    )


@app.route("/sitemap-analysis")
def sitemap_analysis():
    domain = request.args.get('domain')
    if not domain:
        return {
            "error": "No domain specified",
        }

    results = sitemaps.get_all_sitemap_results([domain])[domain]

    # Results can get _very_ big, like megabytes big. We'll default to short and
    # sweet responses
    if 'all' not in request.args:
        for result in results:
            if result == '_meta':
                continue
            # Just return total count instead of all posts
            results[result] = len(results[result])

    return results
