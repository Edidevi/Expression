import json
import boto3
import base64
import uuid
import os

rekognition = boto3.client('rekognition')
s3 = boto3.client('s3')
BUCKET = os.environ['WEBSITE_BUCKET']

def lambda_handler(event, context):
    path = event.get('rawPath', '')
    method = event.get('requestContext', {}).get('http', {}).get('method', '')

    if method == 'GET' and path == '/gallery':
        return get_gallery()
    elif method == 'POST' and path == '/detect':
        return detect_emotion(event)
    else:
        return response(404, {'error': 'Not found'})

def detect_emotion(event):
    try:
        body = json.loads(event['body'])
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
        emotion = top_emotion['TYPE']
        confidence = round(top_emotion['Confidence'], 1)

        key = f'gallery/{uuid.uuid4()}.jpg'
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=image_data,
            ContentType='image/jpeg',
            Metadata={'emotion': emotion, 'confidence': str(confidence)}
        )

        return response(200, {
            'emotion': emotion,
            'confidence': confidence,
            'imageKey': key
        })

    except Exception as e:
        return response(500, {'error': str(e)})

def get_gallery():
    try:
        result = s3.list_objects_v2(Bucket=BUCKET, Prefix='gallery/')
        items = []
        for obj in result.get('Contents', []):
            key = obj['Key']
            meta = s3.head_object(Bucket=BUCKET, Key=key)['Metadata']
            items.append({
                'url': f'https://{BUCKET}.s3.amazonaws.com/{key}',
                'emotion': meta.get('emotion', 'UNKNOWN'),
                'confidence': meta.get('confidence', '0')
            })
        items.reverse()
        return response(200, {'photos': items})
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
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, GET, OPTIONS'
    }
