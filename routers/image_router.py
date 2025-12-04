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

router = APIRouter(prefix="/api/image", tags=["image"])

class ImageAnalyzeRequest(BaseModel):
    # prefer s3_key for private objects; fallback to image_url if necessary
    s3_key: Optional[str] = None
    image_url: Optional[str] = None
    history_id: Optional[int] = None
    influencer_name: Optional[str] = None
    user_nickname: Optional[str] = None

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

    # Call orchestrator/analyze to run color + emotion + influencer chain.
    # Orchestrator requires user_text, we provide a short informative text.
    try:
        orch_payload = svc_orch.OrchestratorRequest(
            user_text=f"이미지 기반 퍼스널컬러 감지: primary={primary or ''}, sub={sub or ''}",
            conversation_history=None,
            personal_color=(primary or None),
            user_nickname=req.user_nickname,
            influencer_name=req.influencer_name,
            use_color=True,
            use_emotion=True,
        )
        orch_resp = await svc_orch.analyze(orch_payload)
    except Exception as e:
        traceback.print_exc()
        logger.error("orchestrator analyze failed: %s", e, exc_info=True)
        orch_resp = {"error": str(e)}

    # If caller provided a history_id, persist the orchestrator result as an AI ChatMessage
    try:
        if req.history_id:
            db = SessionLocal()
            try:
                chat_history = db.query(models.ChatHistory).filter_by(id=req.history_id).first()
                if chat_history:
                    # persist influencer_name on the chat history when provided
                    try:
                        if req.influencer_name and not getattr(chat_history, 'influencer_name', None):
                            chat_history.influencer_name = req.influencer_name
                            db.add(chat_history)
                            db.commit()
                            db.refresh(chat_history)
                    except Exception:
                        pass
                    # try to produce a human-friendly description from orchestrator
                    orch_serializable = None
                    if hasattr(orch_resp, 'dict'):
                        try:
                            orch_serializable = orch_resp.dict()
                        except Exception:
                            orch_serializable = None
                    elif isinstance(orch_resp, dict):
                        orch_serializable = orch_resp

                    desc = None
                    try:
                        if isinstance(orch_serializable, dict):
                            # color parsed description
                            c = orch_serializable.get('color') or {}
                            if isinstance(c, dict):
                                parsed = c.get('parsed') or c.get('detected_color_hints') or c
                                if isinstance(parsed, dict):
                                    desc = parsed.get('description') or parsed.get('reason') or None
                            if not desc:
                                e = orch_serializable.get('emotion') or {}
                                if isinstance(e, dict):
                                    parsed_e = e.get('parsed') or e
                                    if isinstance(parsed_e, dict):
                                        desc = parsed_e.get('description') or parsed_e.get('summary') or None
                    except Exception:
                        desc = None

                    text = desc or '이미지 분석 결과가 저장되었습니다.'
                    raw_text = orch_serializable if orch_serializable is not None else str(orch_resp)
                    try:
                        raw_json = json.dumps(raw_text, ensure_ascii=False)
                    except Exception:
                        raw_json = json.dumps({'orchestrator': str(orch_resp)})

                    ai_msg = models.ChatMessage(
                        history_id=req.history_id,
                        role='ai',
                        text=text,
                        raw=raw_json,
                    )
                    db.add(ai_msg)
                    db.commit()
            finally:
                try:
                    db.close()
                except Exception:
                    pass
    except Exception:
        # non-fatal: if DB write fails, log and continue returning the analysis
        logger.exception('이미지 분석 결과를 채팅 히스토리에 저장하지 못했습니다')

    return {"image_result": res, "orchestrator": orch_resp}
