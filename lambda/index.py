import json
import boto3
import base64
import uuid
import os
from datetime import datetime

rekognition = boto3.client('rekognition')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

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
    else:
        return response(404, {'error': 'Not found'})

def get_user_id(event):
    try:
        claims = event['requestContext']['authorizer']['jwt']['claims']
        return claims['sub']
    except:
        return None

def get_advice(emotion, reason, previous_resolutions):
    try:
        previous_text = ''
        if previous_resolutions:
            previous_text = f"In the past when they felt {emotion}, what helped them was: {', '.join(previous_resolutions[-3:])}."

        prompt = f"""You are a compassionate mental health support assistant. 
A person is feeling {emotion}.
{f'They say: "{reason}"' if reason else ''}
{previous_text}

Give them warm, practical, evidence-based advice in 3-4 sentences. 
Include one specific technique they can try right now.
Be conversational, kind and non-clinical.
Do not start with "I" and do not mention that you are an AI."""

        response_body = bedrock.invoke_model(
            modelId='us.anthropic.claude-haiku-4-5-20251001-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 300,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ]
            })
        )

        result = json.loads(response_body['body'].read())
        return result['content'][0]['text']

    except Exception as e:
        print(f"Bedrock error: {str(e)}")
        return f"Remember that it's okay to feel {emotion.lower()}..."
    
def detect_emotion(event, user_id):
    try:
        body = json.loads(event['body'])
        reason = body.get('reason')

        # Phase 2: confirmed/corrected emotion, generate advice and save
        if reason is not None:
            emotion = body.get('emotion', 'UNKNOWN')
            confidence = body.get('confidence', 0)

            table = dynamodb.Table(TABLE)
            previous = get_previous_resolutions(user_id, emotion, table)
            advice = get_advice(emotion, reason, previous)

            personal_suggestion = None
            if previous:
                personal_suggestion = f"Last time you felt {emotion}, what helped you was: {previous[-1]}"

            entry_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            table.put_item(Item={
                'userId': user_id,
                'entryId': entry_id,
                'timestamp': timestamp,
                'emotion': emotion,
                'confidence': str(confidence),
                'reason': reason,
                'photoKey': '',
                'resolved': False,
                'resolution': ''
            })

            return response(200, {
                'emotion': emotion,
                'confidence': confidence,
                'entryId': entry_id,
                'advice': advice,
                'personalSuggestion': personal_suggestion
            })

        # Phase 1: detect only, don't save
        image_data = base64.b64decode(body['image'])

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

        return response(200, {
            'emotion': emotion,
            'confidence': confidence
        })

    except Exception as e:
        return response(500, {'error': str(e)})

def get_previous_resolutions(user_id, emotion, table):
    try:
        result = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id)
        )
        resolved = [
            i['resolution'] for i in result['Items']
            if i['emotion'] == emotion and i.get('resolved') and i.get('resolution')
        ]
        return resolved
    except:
        return []

def get_entries(user_id):
    try:
        table = dynamodb.Table(TABLE)
        result = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id)
        )
        items = sorted(result['Items'], key=lambda x: x['timestamp'], reverse=True)

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
        resolution = body.get('resolution', '')
        reason = body.get('reason', '')

        table = dynamodb.Table(TABLE)
        table.update_item(
            Key={'userId': user_id, 'entryId': entry_id},
            UpdateExpression='SET resolved = :r, resolution = :res, reason = :reason',
            ExpressionAttributeValues={
                ':r': True if resolution else False,
                ':res': resolution,
                ':reason': reason
            }
        )

        return response(200, {'message': 'Entry updated'})
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
