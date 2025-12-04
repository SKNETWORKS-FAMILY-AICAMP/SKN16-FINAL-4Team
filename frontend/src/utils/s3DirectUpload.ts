import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

/**
 * Browser direct upload to S3 using static credentials from env vars.
 * NOTE: Embedding long-lived credentials in frontend is insecure for production.
 * Use Cognito / STS temporary credentials or presigned URLs in production.
 *
 * Required env (Vite):
 * - VITE_S3_BUCKET
 * - VITE_AWS_REGION
 * - VITE_AWS_ACCESS_KEY_ID
 * - VITE_AWS_SECRET_ACCESS_KEY
 */
export async function uploadDirectToS3(file: File): Promise<{ url: string }>{
  const bucket = import.meta.env.VITE_S3_BUCKET as string | undefined;
  const region = (import.meta.env.VITE_AWS_REGION as string) || 'us-east-1';
  const accessKey = import.meta.env.VITE_AWS_ACCESS_KEY_ID as string | undefined;
  const secretKey = import.meta.env.VITE_AWS_SECRET_ACCESS_KEY as string | undefined;

  if (!bucket || !accessKey || !secretKey) {
    throw new Error('AWS 설정이 누락되었습니다. VITE_S3_BUCKET, VITE_AWS_ACCESS_KEY_ID, VITE_AWS_SECRET_ACCESS_KEY가 필요합니다.');
  }

  const client = new S3Client({
    region,
    credentials: {
      accessKeyId: accessKey,
      secretAccessKey: secretKey,
    },
  });

  const safeName = `${Date.now()}_${Math.random().toString(36).slice(2)}_${file.name}`;
  const key = `uploads/${safeName}`;

  const cmd = new PutObjectCommand({
    Bucket: bucket,
    Key: key,
    Body: file,
    ContentType: file.type || 'application/octet-stream',
    ACL: 'public-read',
  });

  // send the upload
  await client.send(cmd);

  const url = `https://${bucket}.s3.${region}.amazonaws.com/${encodeURIComponent(key)}`;
  return { url };
}
