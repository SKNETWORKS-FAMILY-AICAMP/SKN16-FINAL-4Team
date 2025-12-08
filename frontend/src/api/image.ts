import apiClient from './client';

export interface LabValues {
  L: number;
  a: number;
  b: number;
}

export interface BestType {
  name: string;
  name_eng: string;
  season: string;
  description: string;
}

export interface Top3Item {
  name: string;
}

export interface ImageResult {
  status: string;
  message: string;
  lab_values: LabValues;
  season: string;
  best_type: BestType;
  top3: Top3Item[];
  visualization_b64: string;
}

export interface ImageAnalyzeResponse {
  image_result: ImageResult;
  orchestrator?: any;
}

export interface MakeupResponse {
  key: string;
  url: string;
}

export async function analyzeImage(s3_key: string, history_id?: number, influencer_name?: string, user_nickname?: string) {
  const body: any = { s3_key };
  if (history_id) body.history_id = history_id;
  if (influencer_name) body.influencer_name = influencer_name;
  if (user_nickname) body.user_nickname = user_nickname;
  const res = await apiClient.post<ImageAnalyzeResponse>('/image/analyze', body, { timeout: 60000 });
  return res.data;
}

export async function applyMakeup(s3_key: string, personal_color: string, external_response?: any) {
  const res = await apiClient.post<MakeupResponse>('/image/makeup', { s3_key, personal_color, external_response });
  return res.data;
}
