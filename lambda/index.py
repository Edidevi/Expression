import json
import boto3
import base64

rekognition = boto3.client('rekognition')

def lambda_handler(event, context):
    try:
        # Get the base64 image from the request
        body = json.loads(event['body'])
        image_data = base64.b64decode(body['image'])

        # Call Rekognition
        response = rekognition.detect_faces(
            Image={'Bytes': image_data},
            Attributes=['ALL']
        )

        faces = response['FaceDetails']

        if not faces:
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({'emotion': 'No face detected', 'confidence': 0})
            }

        # Get the top emotion from the first face
        emotions = faces[0]['Emotions']
        top_emotion = max(emotions, key=lambda x: x['Confidence'])

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'emotion': top_emotion['Type'],
                'confidence': round(top_emotion['Confidence'], 1)
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }
