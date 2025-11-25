import React, { useState, useMemo } from 'react';

interface Props {
  profile?: any | null;
  src?: string | null;
  name?: string | null;
  emoji?: string;
  className?: string;
  style?: React.CSSProperties;
  imgStyle?: React.CSSProperties;
}

const resolveCandidate = (profile?: any | null, src?: string | null, name?: string | null) => {
  // prefer explicit src
  if (src) return src;
  if (profile) {
    const raw = profile.profile || profile.image || null;
    if (raw) return String(raw);
  }
  if (name) {
    // user said filenames match influencer.name exactly
    try {
      return `/profiles/${encodeURIComponent(String(name))}.png`;
    } catch (e) {
      return `/profiles/${String(name)}.png`;
    }
  }
  return null;
};

const InfluencerImage: React.FC<Props> = ({ profile, src, name, emoji = '🌟', className, style, imgStyle }) => {
  const [ok, setOk] = useState(true);

  const candidate = useMemo(() => resolveCandidate(profile, src, name), [profile, src, name]);

  if (!candidate) {
    return <span className={className} style={{ fontSize: style?.width ? undefined : 18, ...style }}>{emoji}</span>;
  }

  if (!ok) {
    return <span className={className} style={{ fontSize: 18, ...style }}>{emoji}</span>;
  }

  return (
    <img
      className={className}
      src={candidate}
      alt={`${name || (profile && profile.name) || 'influencer'} profile`}
      style={{ display: 'block', width: '100%', height: '100%', objectFit: 'contain', objectPosition: 'center', ...imgStyle }}
      onError={() => setOk(false)}
    />
  );
};

export default InfluencerImage;
