# authorize_api.py

import requests
import datetime
import json
from config import API_URL, API_LOGIN_ID, TRANSACTION_KEY,REST_API_URL




def make_authorize_net_request(payload):
    headers = {
         
            'Content-Type': 'application/json'
        }
    response = requests.post(API_URL,headers=headers,json=payload)
    response_text = response.content.decode('utf-8-sig')
    return json.loads(response_text)

def get_settled_batch_list():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)

    request_body = {
        "getSettledBatchListRequest": {
            "merchantAuthentication": {
                "name": API_LOGIN_ID,
                "transactionKey": TRANSACTION_KEY
            },
            "firstSettlementDate": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "lastSettlementDate": end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    }
    return make_authorize_net_request(request_body)

def get_transaction_list(batch_id):
    request_body = {
        "getTransactionListRequest": {
            "merchantAuthentication": {
                "name": API_LOGIN_ID,
                "transactionKey": TRANSACTION_KEY
            },
            "batchId": batch_id
        }
    }
    response = make_authorize_net_request(request_body)
    return response.get("transactions", [])
def get_held_transaction_list():
    request_body = {
        "getUnsettledTransactionListRequest": {
            "merchantAuthentication": {
                "name": API_LOGIN_ID,
                "transactionKey": TRANSACTION_KEY
            },
            #"refId": "12345",  # You can make this dynamic as needed
            "status": "pendingApproval",
            "sorting": {
                "orderBy": "submitTimeUTC",
                "orderDescending": False
            },
            "paging": {
                "limit": "100",
                "offset": "1"
            }
        }
    }
    return make_authorize_net_request(request_body)


def get_unsettled_transaction_list():
    request_body = {
        "getUnsettledTransactionListRequest": {
            "merchantAuthentication": {
                "name": API_LOGIN_ID,
                "transactionKey": TRANSACTION_KEY
            }
        }
    }
    return make_authorize_net_request(request_body)
