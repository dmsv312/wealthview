urls = {
    "cs_us": f"https://eodhistoricaldata.com/api/exchanges/US?api_token=3fa9o8ba134f90.20329410&fmt=json",
    "cs_ru": f"https://eodhistoricaldata.com/api/exchanges/MCX?api_token=3fa9o8ba134f90.20329410&fmt=json",
    # "tf_us": f"https://eodhistoricaldata.com/api/exchanges/US?api_token=3fa9o8ba134f90.20329410&fmt=json",
    # "tf_ru": f"https://eodhistoricaldata.com/api/exchanges/MCX?api_token=3fa9o8ba134f90.20329410&fmt=json",
    # "ind": f"https://eodhistoricaldata.com/api/exchanges/INDX?api_token=3fa9o8ba134f90.20329410&fmt=json",
}

"""
..............................................................................................................
................................................ GET DATA ....................................................
..............................................................................................................
"""


# TODO: null
def get_json(url):
    import fios.web.webkit as webkit
    import json
    html = webkit.get_html(url)
    data = json.loads(html)
    return data


def get_unique_values(data, parameter):
    results = set()
    for item in data:
        value = dict(item).get(parameter)
        if value is None:
            # print(item)
            pass

        results.add(value)

    return results


def get_filtered_items(data, filter_item: dict):
    results = []
    (key, value), = filter_item.items()
    for item in data:
        if dict(item).get(key) == value:
            results.append(item)
    return results


def get_data():
    # init
    parameter = "Exchange"
    filter_item = {"Type": None}
    # start loop
    for i, url in enumerate(urls.values()):
        # get data
        print("<< %s >>" % str(i))
        data = get_json(url)
        # hook
        # values = get_unique_values(data, parameter)
        items = get_filtered_items(data, filter_item)
        # show results
        # print("{parameter}: {arr}".format(parameter=parameter, arr=values))
        [print(x) for x in items]


"""
..............................................................................................................
................................................ FILL DB .....................................................
..............................................................................................................
"""


# TODO: Set new data?
# TODO: Countries: by name, None: true
# TODO: Currencies: by code, None: false
# TODO: Exchanges: by code, allow ''. None: true
def check_codes(items):
    # TODO: # Indices: {'EWN', 'ACWI', 'JPN'}
    # TODO: # Stock: intersection EN - RU
    from backtest.models import Asset
    json_items = set(x["Code"] for x in items)
    # sqlite_items = set(x.exchange_ticker for x in Asset.objects.filter(type_id="ST"))
    # sqlite_items = set(x.exchange_ticker for x in Asset.objects.filter(type_id="ET"))
    sqlite_items = set(x.exchange_ticker for x in Asset.objects.filter(type_id="AC"))
    print(json_items - sqlite_items)


"""
..............................................................................................................
................................................ POPULATE ......................................................
..............................................................................................................
"""


def populate():
    import fios.io.console as console
    # init
    # filter_item = {"Type": "Common Stock"}
    # filter_item = {"Type": "ETF"}
    filter_item = {"Type": "INDEX"}
    results = {
    }
    # start loop
    for i, url in enumerate(urls.values()):
        # get data
        print("<< %s >>" % str(i))
        data = get_json(url)
        # get items
        items = get_filtered_items(data, filter_item)
        check_codes(items)
        # create instances
        # response = create_instances(items, type_code="ST", signature="[{}] {}".format(str(i), url))
        # response = create_instances(items, type_code="ET", signature="[{}] {}".format(str(i), url))
        # response = create_instances(items, type_code="AC", signature="[{}] {}".format(str(i), url))

        response = {
            "signature": "...",
            "already_exist": [],
            "created": [],
        }

        results[response["signature"]] = {
            "already_exist": response["already_exist"],
            "not_created": response["not_created"],
        }
    console.notify("... All instances created ...")
    return results


def create_instances(data, type_code, signature):
    from .models import Asset, Country
    import fios.io.console as console
    response = {
        "signature": signature,
        "already_exist": [],
        "not_created": [],
    }
    length = len(data)
    for i, item_data in enumerate(data):
        # init args
        args = {
            "type_id": type_code,
            "exchange_ticker": item_data["Code"],
            "name": get_name(item_data),
            "currency_id": item_data["Currency"],
        }
        if item_data["Exchange"] != "":
            args["exchange_id"] = item_data["Exchange"]
        if item_data["Country"] not in ['Unknown', '']:
            args["country"] = Country.objects.get(name=item_data["Country"])
        # init model
        asset = Asset(**args)
        dumped = dump_item(asset)
        # if already_exist
        if Asset.objects.filter(
                exchange_ticker=asset.exchange_ticker,
                name=asset.name,
                type=asset.type,
                country=asset.country,
                currency=asset.currency
        ).exists():
            console.notify("{i}/{l} {instance} | checked!".format(i=i + 1, l=length, instance=dumped))
            response["already_exist"].append(dumped)
        # if available create
        else:
            console.notify("{i}/{l} {instance} | not exist! ".format(i=i + 1, l=length, instance=dumped),
                           end="")
            # asset.save()
            # console.notify("created!")
            response["not_created"].append(dumped)

    return response


def get_name(item_data: dict):
    name = item_data["Name"]
    if name is None:
        return item_data["Code"]
    else:
        return name


def dump_item(item):
    if item.exchange is None:
        exchange = "null"
    else:
        exchange = item.exchange.code
    return "{type} [{ticker}]: {country}, {exchange}, {currency}".format(
        type=item.type,
        ticker=item.exchange_ticker,
        country=item.country,
        exchange=exchange,
        currency=item.currency,
    )
