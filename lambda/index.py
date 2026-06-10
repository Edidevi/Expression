import json
import boto3
import base64
import uuid
import os
from datetime import datetime

rekognition = boto3.client('rekognition')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET = os.environ['WEBSITE_BUCKET']
TABLE = os.environ['DYNAMODB_TABLE']

def lambda_handler(event, context):
    path = event.get('rawPath', '')
    method = event.get('requestContext', {}).get('http', {}).get('method', '')
    user_id = get_user_id(event)

    if not user_id:
        return response(401, {'error': 'Unauthorised'})

    if method == 'POST' and path == '/detect':
        return detect_emotion(event, user_id)
    elif method == 'GET' and path == '/entries':
        return get_entries(user_id)
    elif method == 'POST' and path == '/resolve':
        return resolve_entry(event, user_id)
    elif method == 'GET' and path == '/suggest':
        return get_suggestion(event, user_id)
    else:
        return response(404, {'error': 'Not found'})

def get_user_id(event):
    try:
        claims = event['requestContext']['authorizer']['jwt']['claims']
        return claims['sub']
    except:
        return None

def detect_emotion(event, user_id):
    try:
        body = json.loads(event['body'])
        image_data = base64.b64decode(body['image'])
        reason = body.get('reason', '')

        result = rekognition.detect_faces(
            Image={'Bytes': image_data},
            Attributes=['ALL']
        )

        faces = result['FaceDetails']
        if not faces:
            return response(200, {'emotion': 'No face detected', 'confidence': 0})

        emotions = faces[0]['Emotions']
        top_emotion = max(emotions, key=lambda x: x['Confidence'])
        emotion = top_emotion['Type']
        confidence = round(top_emotion['Confidence'], 1)

        # Save photo to S3
        photo_key = f'photos/{user_id}/{uuid.uuid4()}.jpg'
        s3.put_object(
            Bucket=BUCKET,
            Key=photo_key,
            Body=image_data,
            ContentType='image/jpeg'
        )

        # Save entry to DynamoDB
        entry_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        table = dynamodb.Table(TABLE)
        table.put_item(Item={
            'userId': user_id,
            'entryId': entry_id,
            'timestamp': timestamp,
            'emotion': emotion,
            'confidence': str(confidence),
            'reason': reason,
            'photoKey': photo_key,
            'resolved': False,
            'resolution': ''
        })

        # Check for previous similar mood suggestion
        suggestion = get_previous_suggestion(user_id, emotion, table)

        return response(200, {
            'emotion': emotion,
            'confidence': confidence,
            'entryId': entry_id,
            'suggestion': suggestion
        })

    except Exception as e:
        return response(500, {'error': str(e)})

def get_entries(user_id):
    try:
        table = dynamodb.Table(TABLE)
        result = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id)
        )
        items = sorted(result['Items'], key=lambda x: x['timestamp'], reverse=True)

        # Add photo URLs
        for item in items:
            if item.get('photoKey'):
                item['photoUrl'] = f'https://{BUCKET}.s3.amazonaws.com/{item["photoKey"]}'

        return response(200, {'entries': items})
    except Exception as e:
        return response(500, {'error': str(e)})

def resolve_entry(event, user_id):
    try:
        body = json.loads(event['body'])
        entry_id = body['entryId']
        resolution = body['resolution']

        table = dynamodb.Table(TABLE)
        table.update_item(
            Key={'userId': user_id, 'entryId': entry_id},
            UpdateExpression='SET resolved = :r, resolution = :res',
            ExpressionAttributeValues={':r': True, ':res': resolution}
        )

        return response(200, {'message': 'Entry updated'})
    except Exception as e:
        return response(500, {'error': str(e)})

def get_previous_suggestion(user_id, emotion, table):
    try:
        result = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id)
        )
        previous = [
            i for i in result['Items']
            if i['emotion'] == emotion and i.get('resolved') and i.get('resolution')
        ]
        if previous:
            latest = sorted(previous, key=lambda x: x['timestamp'], reverse=True)[0]
            return f"Last time you felt {emotion}, what helped you was: {latest['resolution']}"
        return None
    except:
        return None

def get_suggestion(event, user_id):
    try:
        emotion = event.get('queryStringParameters', {}).get('emotion', '')
        table = dynamodb.Table(TABLE)
        result = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id)
        )
        resolved = [
            i for i in result['Items']
            if i['emotion'] == emotion and i.get('resolved') and i.get('resolution')
        ]
        if not resolved:
            return response(200, {'suggestion': None})

        resolutions = [i['resolution'] for i in resolved]
        return response(200, {
            'suggestion': f"Last time you felt {emotion}, what helped was: {resolutions[-1]}",
            'history': resolutions
        })
    except Exception as e:
        return response(500, {'error': str(e)})

def response(status, body):
    return {
        'statusCode': status,
        'headers': cors_headers(),
        'body': json.dumps(body)
    }

def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'POST, GET, OPTIONS'
    }
