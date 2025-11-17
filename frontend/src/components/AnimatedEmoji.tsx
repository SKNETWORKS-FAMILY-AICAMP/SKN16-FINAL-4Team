import React, { useRef, useState, useEffect } from 'react';
import { Player } from '@lottiefiles/react-lottie-player';
import type { EmotionType } from '@/api/chatbot';


const emotionToLottie: Record<EmotionType, string> = {
  happy: '/lotties/happy.json', // smiling face
  sad: '/lotties/sad.json',
  angry: '/lotties/angry.json',
  love: '/lotties/love.json',
  fearful: '/lotties/fearful.json', // side to side worried face
  neutral: '/lotties/neutral.json', // wink face
};

interface AnimatedEmojiProps {
  emotion: EmotionType;
  size?: number;
}

const AnimatedEmoji: React.FC<AnimatedEmojiProps> = ({ emotion, size = 48 }) => {
  const lottieSrc = emotionToLottie[emotion] || emotionToLottie['neutral'];
  // stages: 'enter' -> 'hold' -> 'rest'
  const [stage, setStage] = useState<'enter' | 'hold' | 'rest'>('enter');
  const [isInteractive, setIsInteractive] = useState(false);
  const timeouts = useRef<number[]>([]);

  useEffect(() => {
    // reset to enter whenever emotion changes
    setStage('enter');
    setIsInteractive(false);
    // enter -> after 600ms -> hold -> after 2000ms -> rest
    const t1 = window.setTimeout(() => setStage('hold'), 600);
    const t2 = window.setTimeout(() => setStage('rest'), 600 + 2000);
    timeouts.current.push(t1 as unknown as number, t2 as unknown as number);

    return () => {
      timeouts.current.forEach(id => window.clearTimeout(id));
      timeouts.current = [];
    };
  }, [emotion]);

  const handleInteractive = () => {
    setIsInteractive(true);
    // clear any existing interactive timeout
    timeouts.current.forEach(id => window.clearTimeout(id));
    timeouts.current = [];
    const t = window.setTimeout(() => setIsInteractive(false), 700);
    timeouts.current.push(t as unknown as number);
  };

  // compute transform & transition based on stage / interactive
  let transform = 'scale(1) translate(0,0) rotate(0deg)';
  let transition = 'transform 600ms cubic-bezier(.42,0,.58,1)';

  if (stage === 'enter') {
    transform = 'scale(1.6) translate(-14%, -14%) rotate(0deg)';
    transition = 'transform 600ms cubic-bezier(.42,0,.58,1)';
  } else if (stage === 'hold') {
    transform = 'scale(1.18) translate(0,0) rotate(0deg)';
    transition = 'transform 400ms cubic-bezier(.42,0,.58,1)';
  } else if (stage === 'rest') {
    transform = 'scale(1) translate(0,0) rotate(0deg)';
    transition = 'transform 600ms cubic-bezier(.42,0,.58,1)';
  }

  if (isInteractive) {
    // make interactive feel snappy and bouncy
    transform = 'scale(1.22) translate(-6%, -6%) rotate(2deg)';
    transition = 'transform 350ms cubic-bezier(.2, .8, .2, 1)';
  }

  return (
    <div
      style={{
        width: size,
        height: size,
        display: 'inline-block',
        cursor: 'pointer',
        transformOrigin: 'bottom left',
        transform,
        transition,
      }}
      onClick={handleInteractive}
    >
      <Player
        autoplay
        loop
        src={lottieSrc}
        style={{ width: size, height: size }}
      />
    </div>
  );
};

export default AnimatedEmoji;
