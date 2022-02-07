import asyncio
from urllib.parse import urlencode, urlparse

import aiohttp


# TODO: Move out of here
api_key = '7d49c4bb23310bf6942c0ec8f47cd2ec56ceab7989f071f06891a5ebf818b478'


def _extract_results(data):
    results = data['organic_results']
    # Let's sort to be on the safe side
    results = sorted(results, key=lambda x: x['position'])
    return results


async def _fetch(session, url):
    async with session.get(url) as response:
        data = await response.json()
    return data


async def _fetch_all(session, urls):
    tasks = []

    for url in urls:
        task = asyncio.create_task(_fetch(session, url))
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    return results


def _format_url(url, page):
    if page > 1:
        start = page * 10
        url = url + '&start={}'.format(start)
    return url


async def perform_search(query, target_amount, start_page=None):
    template_url = 'https://serpapi.com/search.json?{}'.format(
        urlencode({
            'q': query,
            'api_key': api_key,
        }),
    )

    # Usually 10 results are returned per page, so under that assumption, we
    # need to fetch at least `target_amount / 10` pages (and maybe more if there
    # are a lot of ads)
    pages = target_amount // 10
    if target_amount % 10:
        pages += 1

    if not start_page:
        start_page = 1
    end_page = start_page + pages - 1

    urls = [
        _format_url(template_url, page)
        for page in range(start_page, end_page + 1)
    ]

    async with aiohttp.ClientSession() as session:
        all_pages = await _fetch_all(session, urls)

    results = []
    for page in all_pages:
        page_results = _extract_results(page)
        results.extend(page_results)

    # If there were ads, then maybe one page returns 7 organic results instead
    # of 10, so we'll need to make up for it
    while len(results) < target_amount:
        new_target_amount = target_amount - len(results)
        new_results = await perform_search(
            query, new_target_amount, start_page=end_page + 1,
        )
        if len(new_results) > new_target_amount:
            new_results = new_results[:new_target_amount]

        results.extend(new_results)

    # Add actual positions to the results (instead of their position on page
    # that they were fetched on)
    counter = 1
    for result in results:
        result['position'] = counter
        counter += 1

    return results


def search(query, target_amount):
    results = asyncio.run(perform_search(query, target_amount))
    return results


def extract_domains_from_results(results):
    domains = []
    for result in results:
        parsed_url = urlparse(result['link'])
        domain = parsed_url.hostname
        domains.append(domain)
    return domains
