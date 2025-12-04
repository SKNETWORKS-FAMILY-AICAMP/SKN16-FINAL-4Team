from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import sys
import io
import base64
import numpy as np
import cv2

app = FastAPI()

# Try to import classifiers from the image_modeling folder. If running from
# a different working directory, add the repo root to sys.path.
try:
    from image_modeling.landmark_classifier import RobustLandmarkClassifier
except Exception:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from image_modeling.landmark_classifier import RobustLandmarkClassifier

# Initialize classifiers once at startup
try:
    robust_clf = RobustLandmarkClassifier()
except Exception:
    # If the classifier fails to initialize (missing OpenCV models etc.), keep None
    robust_clf = None

def _read_image_from_upload(upload: UploadFile) -> np.ndarray:
    data = upload.file.read()
    if not data:
        raise ValueError("empty file")
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("unable to decode image")
    return img

def _encode_image_to_base64(img: np.ndarray) -> str:
    ok, buf = cv2.imencode('.png', img)
    if not ok:
        raise ValueError("failed to encode image")
    b64 = base64.b64encode(buf.tobytes()).decode('ascii')
    return f"data:image/png;base64,{b64}"

def _sanitize_result_for_json(result: Dict[str, Any]) -> Dict[str, Any]:
    # Convert numpy types and remove raw visualization
    out = {}
    for k, v in result.items():
        if isinstance(v, (np.floating, np.integer)):
            out[k] = float(v)
        elif isinstance(v, np.ndarray):
            out[k] = v.tolist()
        else:
            out[k] = v
    return out

class PredictResponse(BaseModel):
    status: str
    message: Optional[str]
    result: Optional[Dict[str, Any]]

@app.get("/api/image/ping")
async def ping():
    return {"status": "ok", "service": "api_image"}

@app.post("/api/image/predict", response_model=PredictResponse)
async def predict_personal_color(file: UploadFile = File(...)):
    # Validate upload first so we can return a clear 400 for bad files
    try:
        img = _read_image_from_upload(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    if robust_clf is None:
        raise HTTPException(status_code=500, detail="Classifier not available")

    try:
        raw_res = robust_clf.classify(img)

        # Extract visualization and encode
        vis = raw_res.pop('visualization', None)
        if vis is not None:
            try:
                vis_b64 = _encode_image_to_base64(vis)
            except Exception:
                vis_b64 = None
        else:
            vis_b64 = None

        sanitized = _sanitize_result_for_json(raw_res)
        if vis_b64:
            sanitized['visualization_b64'] = vis_b64

        return PredictResponse(status="success", message="분석 완료", result=sanitized)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실패: {e}")

@app.post("/api/image/extract_features")
async def extract_features(file: UploadFile = File(...)):
    if robust_clf is None:
        raise HTTPException(status_code=500, detail="Classifier not available")

    try:
        img = _read_image_from_upload(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    try:
        face_roi, masks, vis, eyes_detected = robust_clf.detect_face_and_extract_skin(img)
        if face_roi is None or masks is None:
            raise ValueError("얼굴을 검출할 수 없습니다.")

        features = robust_clf.extract_robust_lab_features(face_roi, masks)
        features_clean = {k: float(v) if isinstance(v, (np.floating, np.integer)) else v for k, v in features.items()}
        # attach visualization
        try:
            features_clean['visualization_b64'] = _encode_image_to_base64(vis)
        except Exception:
            pass

        return {"status": "success", "features": features_clean}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추출 실패: {e}")

