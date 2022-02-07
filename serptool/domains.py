import whois


def get_domain_creation_date(domain):
    data = whois.whois(domain)
    creation_date = data.creation_date

    # Creation date might be a list
    if isinstance(creation_date, list):
        creation_date = creation_date[0]

    return creation_date
