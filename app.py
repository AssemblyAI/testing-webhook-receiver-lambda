import os

import boto3
from boto3.dynamodb.types import TypeSerializer
from flask import Flask, jsonify, make_response, request
from datetime import datetime

app = Flask(__name__)


dynamodb_client = boto3.client('dynamodb')

if os.environ.get('IS_OFFLINE'):
    dynamodb_client = boto3.client(
        'dynamodb', region_name='localhost', endpoint_url='http://localhost:8000'
    )


WEBHOOK_TABLE = os.environ['WEBHOOK_TABLE']


@app.route('/webhook/status/<string:transcript_id>')
def get_transcript_status(transcript_id):
    result = dynamodb_client.get_item(
        TableName=WEBHOOK_TABLE, Key={'transcript_id': {'S': transcript_id}}
    )
    item = result.get('Item')
    if not item:
        return jsonify({'error': 'Could not find status for the provided transcript_id'}), 404

    return jsonify({'transcript_id': item.get('transcript_id').get('S'), 'status': item.get('status').get('S'), 'client_ip': item.get('client_ip').get('S'), 'http_code': item.get('http_code').get('S'), 'file_name': item.get('file_name').get('S'), 'created_at': item.get('created_at').get('S'), 'webhook_headers': item.get('webhook_headers').get('M')})

@app.route('/webhook', methods=['POST'])
def handle_webhook():    
    transcript_id = request.json.get('transcript_id')
    status = request.json.get('status')
    file_name = request.args.get('file_name', default='NOT PROVIDED') # optional file_name param example
    http_code = request.args.get('http_code', default='200') # optional http_code param to return
    now = datetime.now()
    created_at = now.strftime("%m/%d/%Y, %H:%M:%S")
    if request.headers.getlist("X-Forwarded-For"):
        client_ip = request.headers.getlist("X-Forwarded-For")[-1]
    else:
        client_ip = request.remote_addr
    if not transcript_id or not status:
         return jsonify({'error': 'Please provide both "transcript_id" and "status"'}), 400
    webhook_headers = {k: request.headers.getList(k) for k, _ in dict(request.headers).items()}
    dynamodb_client.put_item(
        TableName=WEBHOOK_TABLE, Item={
            'transcript_id': {'S': transcript_id}, 
            'status': {'S': status}, 
            'client_ip': {'S': client_ip}, 
            'http_code': {'S': http_code}, 
            'file_name': {'S': file_name}, 
            'created_at': {'S': created_at}, 
            'webhook_headers': {'M': webhook_headers}
            }
        )
    if http_code in ['400','403','404','429','500','503']:
        return make_response(jsonify({'error': 'Custom error requested', 'transcript_id': transcript_id, 'client_ip': client_ip, 'http_code': http_code}), int(http_code))
    else:
        return jsonify({'transcript_id': transcript_id, 'status': status, 'file_name': file_name, 'client_ip': client_ip, 'http_code': http_code, 'created_at': created_at}), 200

@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error='Not found!'), 404)
