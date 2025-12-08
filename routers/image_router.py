from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import httpx
import logging
import traceback
from starlette.datastructures import UploadFile as StarletteUploadFile
import json

from database import SessionLocal
import models

logger = logging.getLogger(__name__)

# internal services
from services.api_image import main as svc_image
from services.orchestrator import main as svc_orch
from services.api_makeup import main as svc_makeup
from services.api_color import main as svc_color
from virtual_makeup.demo_responses import get_makeup_response

router = APIRouter(prefix="/api/image", tags=["image"])

class ImageAnalyzeRequest(BaseModel):
    # prefer s3_key for private objects; fallback to image_url if necessary
    s3_key: Optional[str] = None
    image_url: Optional[str] = None
    history_id: Optional[int] = None
    influencer_name: Optional[str] = None
    user_nickname: Optional[str] = None

class ImageMakeupRequest(BaseModel):
    s3_key: Optional[str] = None
    image_url: Optional[str] = None
    personal_color: str
    external_response: Optional[dict] = None

@router.post('/presign')
async def presign_upload(payload: dict):
    """
    Return a presigned PUT URL and the S3 key (object will remain private).
    Request payload: { "filename": "photo.jpg", "content_type": "image/jpeg" }
    """
    bucket = os.getenv('S3_BUCKET')
    if not bucket:
        raise HTTPException(status_code=400, detail="S3_BUCKET이 설정되어 있지 않습니다")

    filename = payload.get('filename')
    content_type = payload.get('content_type') or 'application/octet-stream'
    if not filename:
        raise HTTPException(status_code=400, detail="filename이 필요합니다")

    try:
        import boto3
        s3 = boto3.client('s3')
        key = f"uploads/{uuid.uuid4().hex}_{filename}"
        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket, 'Key': key, 'ContentType': content_type},
            ExpiresIn=600,  # 10 minutes
        )
        # Also generate a short-lived presigned GET URL so the client can preview the uploaded private object
        try:
            presigned_get = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=300,  # 5 minutes
            )
        except Exception:
            presigned_get = None

        return {"presigned_url": presigned_url, "key": key, "presigned_get_url": presigned_get}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"presign 생성 실패: {e}")


@router.post('/presign_get')
async def presign_get(payload: dict):
    """
    Return a presigned GET URL for a private S3 object.
    Request payload: { "key": "uploads/xxx.png" }
    """
    bucket = os.getenv('S3_BUCKET')
    if not bucket:
        raise HTTPException(status_code=400, detail="S3_BUCKET이 설정되어 있지 않습니다")

    key = payload.get('key')
    if not key:
        raise HTTPException(status_code=400, detail="key가 필요합니다")

    try:
        import boto3
        s3 = boto3.client('s3')
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=300,  # 5 minutes
        )
        return {"url": presigned_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"presign(get) 생성 실패: {e}")


@router.post('/upload')
async def upload_to_s3(file: UploadFile = File(...)):
    """
    Server-side upload (fallback). Stores object privately and returns S3 key (or local key when S3 not configured).
    """
    bucket = os.getenv('S3_BUCKET')
    data = await file.read()
    if bucket:
        try:
            import boto3
            s3 = boto3.client('s3')
            key = f"uploads/{uuid.uuid4().hex}_{file.filename}"
            # keep object private by default
            s3.put_object(Bucket=bucket, Key=key, Body=data)
            return {"key": key}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"S3 업로드 실패: {e}")
    else:
        try:
            uploads_dir = os.path.join(os.getcwd(), 'static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            path = os.path.join(uploads_dir, filename)
            with open(path, 'wb') as f:
                f.write(data)
            # return a local key that the server can resolve when reading
            local_key = f"local/uploads/{filename}"
            return {"key": local_key}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"파일 저장 실패: {e}")


@router.post('/analyze')
async def analyze_image(req: ImageAnalyzeRequest):
    """
    Analyze image. Prefer `s3_key` which points to a private object in S3 (server will read it).
    If `image_url` is provided, server will download that URL.
    """
    content = None
    filename = f"img_{uuid.uuid4().hex}.jpg"

    # If s3_key provided, read from S3 (or local fallback)
    if req.s3_key:
        bucket = os.getenv('S3_BUCKET')
        # local stored key pattern: local/uploads/{filename}
        if req.s3_key.startswith('local/') and not bucket:
            # read from local filesystem
            try:
                local_path = os.path.join(os.getcwd(), req.s3_key.replace('local/', ''))
                with open(local_path, 'rb') as f:
                    content = f.read()
                filename = os.path.basename(local_path)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"로컬 파일 읽기 실패: {e}")
        else:
            # read from S3
            if not bucket:
                raise HTTPException(status_code=500, detail='S3_BUCKET 설정이 필요합니다')
            try:
                import boto3
                s3 = boto3.client('s3')
                resp = s3.get_object(Bucket=bucket, Key=req.s3_key)
                content = resp['Body'].read()
                filename = os.path.basename(req.s3_key)
            except Exception as e:
                # Log full traceback for diagnosis
                traceback.print_exc()
                logger.error(f"S3 get_object failed for Bucket={bucket} Key={req.s3_key}: %s", e, exc_info=True)
                raise HTTPException(status_code=400, detail=f"S3 객체 읽기 실패: {e}")

    elif req.image_url:
        # download image bytes from provided URL
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(req.image_url)
                resp.raise_for_status()
                content = resp.content
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"이미지 다운로드 실패: {e}")
    else:
        raise HTTPException(status_code=400, detail="s3_key 또는 image_url이 필요합니다")

    # wrap into UploadFile-compatible object and call image classifier
    try:
        bio = memoryview(content).tobytes()
        from io import BytesIO

        file_obj = BytesIO(bio)
        # Starlette's UploadFile does not accept content_type in the constructor in this environment.
        # Create the UploadFile and set content_type afterwards.
        upload = StarletteUploadFile(file=file_obj, filename=filename)
        try:
            upload.content_type = "image/jpeg"
        except Exception:
            # some UploadFile implementations may be immutable; ignore if we can't set it
            pass
        image_resp = await svc_image.predict_personal_color(upload)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        logger.error("predict_personal_color failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"이미지 분석 실패: {e}")

    # extract tone hints
    res = image_resp.result if hasattr(image_resp, 'result') else (image_resp.get('result') if isinstance(image_resp, dict) else None)
    primary = None
    sub = None
    if isinstance(res, dict):
        primary = res.get('primary_tone') or res.get('primary')
        sub = res.get('sub_tone') or res.get('sub')

        # Enrich with makeup recommendations using api_color
        # Process best_type
        if res.get('best_type'):
            best_name = res['best_type'].get('name')
            if best_name:
                try:
                    makeup_rec = svc_color.get_makeup_recommendation(best_name)
                    if makeup_rec:
                        res['best_type'].update(makeup_rec)
                except Exception as e:
                    logger.warning(f"Failed to get makeup rec for best_type: {e}")

        # Process top3
        if res.get('top3'):
            for item in res['top3']:
                name = item.get('name')
                if name:
                    try:
                        # Use static fallback for top3 to avoid RAG timeout
                        makeup_rec = get_makeup_response(name)
                        if makeup_rec:
                            item.update(makeup_rec)
                    except Exception as e:
                        logger.warning(f"Failed to get makeup rec for top3 {name}: {e}")

    # Orchestrator call removed as per requirement:
    # "api_emotion, api_color, api_influencer는 chatbot/analyze api에서만 사용할거야."
    # "이미지 분석할 때는 이미지 분석에 대한 데이터만 받고 싶어."
    
    return {"image_result": res}

@router.post('/makeup')
async def apply_makeup(req: ImageMakeupRequest):
    """
    Apply virtual makeup to an image based on personal color.
    Returns the S3 key and presigned URL of the processed image.
    """
    content = None
    filename = f"makeup_{uuid.uuid4().hex}.jpg"

    # 1. Retrieve image content
    if req.s3_key:
        bucket = os.getenv('S3_BUCKET')
        if req.s3_key.startswith('local/') and not bucket:
            try:
                local_path = os.path.join(os.getcwd(), req.s3_key.replace('local/', ''))
                with open(local_path, 'rb') as f:
                    content = f.read()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"로컬 파일 읽기 실패: {e}")
        else:
            if not bucket:
                raise HTTPException(status_code=500, detail='S3_BUCKET 설정이 필요합니다')
            try:
                import boto3
                s3 = boto3.client('s3')
                resp = s3.get_object(Bucket=bucket, Key=req.s3_key)
                content = resp['Body'].read()
            except Exception as e:
                logger.error(f"S3 get_object failed: {e}")
                raise HTTPException(status_code=400, detail=f"S3 객체 읽기 실패: {e}")

    elif req.image_url:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(req.image_url)
                resp.raise_for_status()
                content = resp.content
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"이미지 다운로드 실패: {e}")
    else:
        raise HTTPException(status_code=400, detail="s3_key 또는 image_url이 필요합니다")

    # 2. Apply makeup
    try:
        result_bytes = svc_makeup.apply_makeup_service(content, req.personal_color, req.external_response)
    except Exception as e:
        logger.error(f"Makeup application failed: {e}")
        raise HTTPException(status_code=500, detail=f"메이크업 적용 실패: {e}")

    # 3. Upload result to S3 (or local)
    bucket = os.getenv('S3_BUCKET')
    result_key = f"uploads/{filename}"
    
    if bucket:
        try:
            import boto3
            s3 = boto3.client('s3')
            s3.put_object(Bucket=bucket, Key=result_key, Body=result_bytes, ContentType='image/jpeg')
            
            # Generate presigned URL for immediate display
            presigned_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': result_key},
                ExpiresIn=3600,  # 1 hour
            )
            return {"key": result_key, "url": presigned_url}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"결과 이미지 업로드 실패: {e}")
    else:
        try:
            uploads_dir = os.path.join(os.getcwd(), 'static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            path = os.path.join(uploads_dir, filename)
            with open(path, 'wb') as f:
                f.write(result_bytes)
            
            # For local dev, return a relative URL if static serving is set up, or just the key
            # Assuming static files are served at /static/uploads
            local_key = f"local/uploads/{filename}"
            # Construct a full URL if possible, or let frontend handle it
            # Here we just return the key and a relative URL
            return {"key": local_key, "url": f"/static/uploads/{filename}"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"결과 파일 저장 실패: {e}")
