import time
import asyncio
import itertools
from urllib.robotparser import RobotFileParser

import aiohttp
from bs4 import BeautifulSoup


# Latest Chrome user agent at the time of writing
user_agent_spoof = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36'

fallback_sitemap_lookups = [
    'post-sitemap{index}.xml',
    'blog/post-sitemap{index}.xml',
]

sitemap_filter_keywords = [
    'blog',
    'post',
]


def _build_url(domain, path):
    return 'https://{}/{}'.format(domain, path)


async def _get_default_sitemaps_from_robots(session, domain):
    robots_url = _build_url(domain, 'robots.txt')
    try:
        async with session.get(robots_url) as response:
            if not response.ok:
                return None
            text = await response.text()
    except (
            aiohttp.ClientConnectionError,
            aiohttp.ClientResponseError,
            asyncio.TimeoutError,
    ) as e:
        return None

    parser = RobotFileParser()
    parser.parse(text.splitlines())
    return parser.site_maps()


def _parse_sitemap(xml):
    if xml.find('sitemapindex'):
        type_ = 'sitemap'
    elif xml.find('urlset'):
        type_ = 'url'
    else:
        return None, []

    targets = []
    for target_el in xml.find_all(type_):
        target = target_el.find('loc').text
        targets.append(target)

    return type_, targets


async def _fetch_sitemap(
        session,
        sitemap,
        from_robots=False,
        *,
        url_index=None,
):
    url_index_fmt = '' if url_index is None else url_index
    url = sitemap.format(index=url_index_fmt)
    try:
        async with session.get(url) as response:
            if not response.ok:
                return {}

            text = await response.text(errors='ignore')
    except (
            aiohttp.ClientConnectionError,
            aiohttp.ClientResponseError,
            asyncio.TimeoutError,
    ) as e:
        return {}

    try:
        xml = BeautifulSoup(text, 'lxml-xml')
    except Exception as e:
        return {}

    type_, targets = _parse_sitemap(xml)

    if type_ not in ['url', 'sitemap']:
        # Invalid data received
        return {}

    results = {}
    if type_ == 'url':
        if targets:
            results[url] = targets

    elif type_ == 'sitemap':
        # Fetch only those that have keywords in name
        filtered_targets = set()
        for target in targets:
            for keyword in sitemap_filter_keywords:
                if keyword in target.lower():
                    filtered_targets.add(target)

        filtered_targets = list(filtered_targets)
        results = await _fetch_sitemaps(session, filtered_targets)

    # If we're bruteforcing our way in, let's continue all the way until we
    # exhaust results
    if from_robots and results:
        next_url_index = url_index + 1 if url_index is not None else 1
        next_results = await _fetch_sitemap(
            session, sitemap, from_robots, url_index=next_url_index,
        )
        results.update(next_results)

    return results


async def _fetch_sitemaps(
        session,
        sitemaps,
        from_robots=False,
        *,
        url_index=None,
):
    tasks = []
    for sitemap in sitemaps:
        task = asyncio.create_task(
            _fetch_sitemap(session, sitemap, from_robots, url_index=url_index),
        )
        tasks.append(task)

    responses = await asyncio.gather(*tasks)

    results = {}

    # All responses are dicts `sitemap_url -> [actual_urls]`
    # Let's just combine them into a single one
    for response in responses:
        results.update(response)

    return results


async def _get_sitemap_entries(session, domain):
    # First, try `robots.txt`
    started = time.time()

    from_robots = True
    domain_sitemaps = await _get_default_sitemaps_from_robots(session, domain)

    sitemap_results = {}
    if domain_sitemaps:
        sitemap_results = await _fetch_sitemaps(
            session, domain_sitemaps,
        )

    if not sitemap_results:
        # Try with the default one
        domain_sitemaps = [
            _build_url(domain, path)
            for path in fallback_sitemap_lookups
        ]

        sitemap_results = await _fetch_sitemaps(
            session, domain_sitemaps, from_robots=True,
        )
        from_robots = False

    elapsed = time.time() - started

    meta = {
        'domain': domain,
        'from_robots': from_robots,
        'elapsed': elapsed,
    }
    if not sitemap_results:
        meta['has_entries'] = False
    else:
        meta['has_entries'] = True
        all_entries = list(
            itertools.chain.from_iterable(sitemap_results.values()),
        )
        meta['num_entries'] = len(all_entries)
        meta['num_entries_unique'] = len(set(all_entries))

    sitemap_results['_meta'] = meta
    return sitemap_results


async def get_all_sitemap_results_async(domains):
    headers = {
        # Spoof user agent everywhere so we don't trigger firewalls (happened
        # with some sites during testing)
        'User-Agent': user_agent_spoof,
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [
            asyncio.create_task(_get_sitemap_entries(session, domain))
            for domain in domains
        ]
        responses = await asyncio.gather(*tasks)

    results = dict(zip(domains, responses))
    return results


def get_all_sitemap_results(domains):
    return asyncio.run(get_all_sitemap_results_async(domains))
