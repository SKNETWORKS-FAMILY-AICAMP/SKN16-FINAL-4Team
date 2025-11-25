import apiClient from './client';
import localProfiles from '@/data/influencers';

export const getInfluencerProfiles = async () => {
  try {
    const res = await apiClient.get('/influencer/profiles');
    return res.data;
  } catch (e) {
    console.warn('Failed to fetch influencer profiles, using local fallback', e);
    return localProfiles;
  }
};

export default { getInfluencerProfiles };
