import apiClient from '@/api/client';

export async function uploadImageToS3(file: File): Promise<{ key: string; url?: string }>{
  // 1) Request presigned URL from backend
  const filename = file.name;
  const content_type = file.type || 'application/octet-stream';
  const presignResp = await apiClient.post('/image/presign', { filename, content_type });
  const { presigned_url, key, presigned_get_url } = presignResp.data;

  // 2) Upload file directly to S3 using PUT
  const putResp = await fetch(presigned_url, {
    method: 'PUT',
    headers: {
      'Content-Type': content_type,
    },
    body: file,
  });

  if (!putResp.ok) {
    const text = await putResp.text().catch(() => '');
    throw new Error(`S3 업로드 실패: ${putResp.status} ${text}`);
  }

  // 3) If the presign endpoint returned a presigned GET URL, use it for preview.
  // This avoids calling an additional API. If not present, return only the key.
  if (presigned_get_url) {
    return { key, url: presigned_get_url };
  }

  return { key };
}
