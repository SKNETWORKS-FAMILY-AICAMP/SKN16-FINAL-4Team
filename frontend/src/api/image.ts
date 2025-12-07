import apiClient from './client';

export interface ImageAnalyzeResponse {
  image_result?: any;
  orchestrator?: any;
}

export interface MakeupResponse {
  status: string;
  makeup_image_url: string;
}

export async function analyzeImage(s3_key: string, history_id?: number, influencer_name?: string, user_nickname?: string) {
  const body: any = { s3_key };
  if (history_id) body.history_id = history_id;
  if (influencer_name) body.influencer_name = influencer_name;
  if (user_nickname) body.user_nickname = user_nickname;
  const res = await apiClient.post<ImageAnalyzeResponse>('/image/analyze', body, { timeout: 60000 });
  return res.data;
}

export async function applyMakeup(s3_key: string, personal_color: string) {
  const res = await apiClient.post<MakeupResponse>('/image/makeup', { s3_key, personal_color });
  return res.data;
}
