import os

import boto3
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
        return jsonify({'error': 'Could not find status for the provided "transcript_id"'}), 404

    return jsonify(
        {'transcript_id': item.get('transcript_id').get('S'), 'status': item.get('status').get('S'), 'file_name': item.get('file_name').get('S'), 'created_at': item.get('created_at').get('S') }
    )


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    transcript_id = request.json.get('transcript_id')
    status = request.json.get('status')
    file_name = request.args.get('file_name', default='NOT PROVIDED') # optional file_name param example
    now = datetime.now()
    created_at = now.strftime("%m/%d/%Y, %H:%M:%S")
    if not transcript_id or not status:
         return jsonify({'error': 'Please provide both "transcript_id" and "status"'}), 400
    dynamodb_client.put_item(
        TableName=WEBHOOK_TABLE, Item={'transcript_id': {'S': transcript_id}, 'status': {'S': status}, 'file_name': {'S': file_name}, 'created_at': {'S': created_at}}
    )
    return jsonify({'transcript_id': transcript_id, 'status': status, 'file_name': file_name, 'created_at': created_at})
   
@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error='Not found!'), 404)
