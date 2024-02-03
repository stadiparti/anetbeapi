# routes.py

from flask import Flask, jsonify, request
import json
import requests
import concurrent.futures
from authorize_api import make_authorize_net_request,get_settled_batch_list, get_transaction_list, get_unsettled_transaction_list, get_held_transaction_list
from config import REDIS_URL, API_AUTHORIZATION_HEADER, API_URL, REST_API_URL, API_LOGIN_ID, TRANSACTION_KEY
import base64
import redis
import certifi
import logging
from concurrent.futures import ThreadPoolExecutor 



logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Base64 encode API credentials
credentials = f"{API_LOGIN_ID}:{TRANSACTION_KEY}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()
API_AUTHORIZATION_HEADER_1 = f"Basic {encoded_credentials}"

def init_routes(app):
      # Redis setup
    redis_client = redis.Redis.from_url(
        REDIS_URL,
        ssl_cert_reqs='required',
        ssl_ca_certs=certifi.where()
    )

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
       

    @app.route('/createinvoice', methods=['POST'])
    def create_invoice():
        headers = {
            'Authorization': API_AUTHORIZATION_HEADER,
            'Content-Type': 'application/json'
        }
        #payload = json.loads(request.data)
        payload = request.get_json(force=True)
    
        logging.info(f"Invoice payload for Authorize.Net: {payload}")

        # Ensure payload is not None or empty before sending
        if payload:
            response = requests.post(REST_API_URL, headers=headers, json=payload)
            return jsonify(response.json())
        else:
            logging.error("Empty payload received.")
            return jsonify({"error": "Empty payload"}), 400
    # Define your existing routes here...

    # Additional functions for handling customer profiles
    def make_auth_net_request(payload):
        headers = {
           # 'Authorization': API_AUTHORIZATION_HEADER_1,
            'Content-Type': 'application/json'
        }
        response = requests.post(API_URL, headers=headers, json=payload)
        try:
            # Decode the response content
            content = response.content.decode('utf-8-sig')
            json_data = json.loads(content)
            
            # Pretty print the JSON data
            print(json.dumps(json_data, indent=4, sort_keys=True))
            return json_data
        except json.JSONDecodeError as e:
            print(f"JSON decoding failed: {e}")
            return None

    def get_all_customer_profile_ids():
        payload = {
            "getCustomerProfileIdsRequest": {
                "merchantAuthentication": {
                    "name": API_LOGIN_ID,
                    "transactionKey": TRANSACTION_KEY
                }
            }
        }
        response_json = make_auth_net_request(payload)
       
        if response_json and 'ids' in response_json:
            # Extract the IDs from the response JSON
            ids = response_json['ids']
            logging.info(f"profiles from Authorize.Net...{ids}")
            return ids
        else:
            logging.error("Failed to retrieve IDs or no IDs present in the response.")
            return []

    def fetch_customer_profile(profile_id):
        payload = {
            "getCustomerProfileRequest": {
                "merchantAuthentication": {
                    "name": API_LOGIN_ID,
                    "transactionKey": TRANSACTION_KEY
                },
                "customerProfileId": profile_id
            }
        }
        response = make_auth_net_request(payload)
        if response:
            return response.get('profile')
        return None

    def store_profile_in_redis(profile_id, profile_data):
        redis_client.set(f"profile:{profile_id}", json.dumps(profile_data))

    def process_profile(profile_id):
        profile_data = fetch_customer_profile(profile_id)
        if profile_data:
            store_profile_in_redis(profile_id, profile_data)

    def is_redis_empty():
        keys = redis_client.keys('profile:*')
        return len(keys) == 0

    def fetch_profiles_from_redis():
        stored_profiles = []
        for key in redis_client.scan_iter("profile:*"):
            profile = json.loads(redis_client.get(key))
            stored_profiles.append(profile)
        return stored_profiles

    @app.route('/getprofiles', methods=['GET'])
    def get_profiles():
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        if is_redis_empty() or refresh:
            logging.info("Refresh requested. Fetching profiles from Authorize.Net...")
            profile_ids = get_all_customer_profile_ids()
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(process_profile, profile_ids[:500])  # Limit to 500 for optimization
            source = "Fetched from Authorize.Net and stored in Redis"
        else:
            source = "Retrieved from Redis Cache"

        profiles = fetch_profiles_from_redis()
        return jsonify({"source": source, "profiles": profiles})
    
    @app.route('/createprofile', methods=['POST'])
    def create_profile():
        # Payload to be sent to Authorize.Net
        profile_data = request.get_json(force=True)
        logging.info(f"Invoice payload for Authorize.Net: {profile_data}")
        # Ensure payload is not None or empty before sending
        if profile_data:
            payload = {
                "createCustomerProfileRequest": {
                    "merchantAuthentication": {
                        "name": API_LOGIN_ID,
                        "transactionKey": TRANSACTION_KEY
                    },
                    "profile": profile_data
                }
            }        
            logging.info(f"Invoice payload for Authorize.Net: {payload}")
            return make_authorize_net_request(payload)
            
        else:
            logging.error("Empty payload received.")
            return jsonify({"error": "Empty payload"}), 400


