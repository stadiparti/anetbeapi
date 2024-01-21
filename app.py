from flask import Flask, jsonify
import requests
import datetime
import json
import concurrent.futures
import routes
from authorize_api import get_settled_batch_list, get_transaction_list, get_unsettled_transaction_list, get_held_transaction_list

app = Flask(__name__)

routes.init_routes(app)

if __name__ == '__main__':
    app.run(debug=True)
