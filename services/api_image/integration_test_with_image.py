# Integration test for api_image using a local image file
# Place your image at one of these paths (checked in order):
#  - services/api_image/sample_face.jpg
#  - image_modeling/augmented_data/봄_트루/sample.jpg
# Or set the IMAGE_PATH environment variable before running this script.

from fastapi.testclient import TestClient
from services.api_image.main import app
import os
import sys

client = TestClient(app)

# candidate paths
candidates = [
    os.environ.get('IMAGE_PATH'),
    'services/api_image/sample_face.png',
    'image_modeling/augmented_data/봄_트루/1.jpg',
    'image_modeling/augmented_data/봄_트루/48.jpg',
]

image_path = None
for p in candidates:
    if p and os.path.exists(p):
        image_path = p
        break

if not image_path:
    print("No image found for integration test.")
    print("Place your test image at 'services/api_image/sample_face.png' or set IMAGE_PATH env var.")
    sys.exit(2)

print(f"Using image: {image_path}")

with open(image_path, 'rb') as f:
    files = {'file': (os.path.basename(image_path), f, 'image/png')}
    # Test predict
    resp = client.post('/api/image/predict', files=files)
    print('\n/predict status:', resp.status_code)
    try:
        j = resp.json()
        # Print concise summary
        print('predict keys:', list(j.keys()))
        res = j.get('result') or {}
        print('result keys:', list(res.keys()))
        # Save visualization if present
        vis_b64 = None
        if isinstance(res, dict):
            vis_b64 = res.get('visualization_b64')
        if vis_b64:
            import base64
            header = 'data:image/png;base64,'
            if vis_b64.startswith(header):
                vis_b64 = vis_b64[len(header):]
            out_path = 'services/api_image/out_predict_visualization.png'
            with open(out_path, 'wb') as outf:
                outf.write(base64.b64decode(vis_b64))
            print('Saved predict visualization to', out_path)
        else:
            print('No visualization returned for predict')
    except Exception as e:
        print('predict response read error:', e)

# reopen file for second request
with open(image_path, 'rb') as f:
    files = {'file': (os.path.basename(image_path), f, 'image/png')}
    resp2 = client.post('/api/image/extract_features', files=files)
    print('\n/extract_features status:', resp2.status_code)
    try:
        j2 = resp2.json()
        print('extract_features keys:', list(j2.keys()))
        features = j2.get('features') or {}
        print('features keys:', list(features.keys()))
        vis_b64 = None
        if isinstance(features, dict):
            vis_b64 = features.get('visualization_b64')
        if vis_b64:
            import base64
            header = 'data:image/png;base64,'
            if vis_b64.startswith(header):
                vis_b64 = vis_b64[len(header):]
            out_path2 = 'services/api_image/out_extract_features_visualization.png'
            with open(out_path2, 'wb') as out2:
                out2.write(base64.b64decode(vis_b64))
            print('Saved extract_features visualization to', out_path2)
        else:
            print('No visualization returned for extract_features')
    except Exception as e:
        print('extract_features response read error:', e)
