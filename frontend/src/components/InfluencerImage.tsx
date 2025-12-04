import React, { useState, useMemo } from 'react';

interface Props {
  src?: string | null;
  name?: string | null;
  emoji?: string;
  className?: string;
  style?: React.CSSProperties;
  imgStyle?: React.CSSProperties;
}

const resolveCandidate = (src?: string | null, name?: string | null) => {
  // prefer explicit src
  if (src) return src;

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

const InfluencerImage: React.FC<Props> = ({ src, name, emoji = '🌟', className, style, imgStyle }) => {
  const [ok, setOk] = useState(true);

  const candidate = useMemo(() => resolveCandidate(src, name), [src, name]);

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
      alt={`${name || 'influencer'} profile`}
      style={{ display: 'block', width: '100%', height: '100%', objectFit: 'fill', objectPosition: 'center', ...imgStyle }}
      onError={() => setOk(false)}
    />
  );
};

export default InfluencerImage;
