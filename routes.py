# routes.py

from flask import Flask, jsonify, request
import json
import requests
import concurrent.futures
from authorize_api import get_settled_batch_list, get_transaction_list, get_unsettled_transaction_list, get_held_transaction_list
from config import API_AUTHORIZATION_HEADER,REST_API_URL,API_LOGIN_ID, TRANSACTION_KEY
import base64


credentials = f"{API_LOGIN_ID}:{TRANSACTION_KEY}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()

API_AUTHORIZATION_HEADER_1 = f"Basic {encoded_credentials}"


def init_routes(app):
    
    @app.route('/getheldtransactions', methods=['GET'])
    def get_held_transactions():
        response = get_held_transaction_list()
        transactions = response.get("transactions", [])
        return jsonify(response)

    @app.route('/gettransactions', methods=['GET'])
    def get_transactions():
        settled_batch_list = get_settled_batch_list().get("batchList", [])
        unsettled_transactions = get_unsettled_transaction_list().get("transactions", [])

        transactions = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(get_transaction_list, batch["batchId"]) for batch in settled_batch_list]
            for future in concurrent.futures.as_completed(futures):
                transactions.extend(future.result())

        transactions.extend(unsettled_transactions)
        transactions.sort(key=lambda x: x["submitTimeUTC"])

        return jsonify(transactions)
   
    @app.route('/getinvoices', methods=['GET'])
    def get_invoices():
        offset = request.args.get('offset', '0')
        limit = request.args.get('limit', '5')
        status = request.args.get('status', 'sent')
        api_url = f"{REST_API_URL}?offset={offset}&limit={limit}&status={status}"

        headers = {
            'Authorization': API_AUTHORIZATION_HEADER,
            'Content-Type': 'application/json'
        }
        response = requests.get(api_url, headers=headers)
        return jsonify(response.json())
        @app.route('/getheldtransactions', methods=['GET'])
        def get_held_transactions():
            response = get_held_transaction_list()
            transactions = response.get("transactions", [])
            return jsonify(response)

    @app.route('/createinvoice', methods=['POST'])
    def create_invoice():
        headers = {
            'Authorization': API_AUTHORIZATION_HEADER,
            'Content-Type': 'application/json'
        }
        payload = json.loads(request.data)
        response = requests.post(REST_API_URL, headers=headers, json=payload)
        return jsonify(response.json())
