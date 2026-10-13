"""Prepare a J-Quants Nikkei225 request plan; this command does not call an API.

Select personal (Premium) or Pro after checking the account's entitlement.
Credentials and actual acquisition are separate from this offline source correction.
"""
from __future__ import annotations
import argparse
from datetime import date
import json
from pathlib import Path


def request_plan(service, trade_date):
    date.fromisoformat(trade_date)
    if service == 'personal':
        base = 'https://api.jquants.com/v2'
        endpoint = '/derivatives/bars/daily/options'
        authentication = 'x-api-key from local credential storage'
        response_array = 'data'
    elif service == 'pro':
        base = 'https://api.jquants-pro.com/v2'
        endpoint = '/derivatives/options'
        authentication = 'Authorization: Bearer token from local credential storage'
        response_array = 'options'
    else:
        raise ValueError('Select personal or pro explicitly')
    return dict(source_service='jquants_personal_v2' if service == 'personal' else 'jquants_pro_v2',
                executed=False, method='GET', url=base+endpoint,
                query=dict(date=trade_date, category='NK225MWE'),
                authentication=authentication, response_array=response_array,
                pagination='Follow pagination_key with the same date/category until absent',
                credentials_loaded=False,
                limitations=['Account entitlement unverified', 'No cash-index OHLC supplied',
                             'This is a request plan, not acquired market data'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--service', choices=['personal', 'pro'], required=True)
    parser.add_argument('--date', required=True)
    args = parser.parse_args()
    print(json.dumps(request_plan(args.service, args.date), ensure_ascii=False, indent=2))
