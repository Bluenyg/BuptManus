'use client';

import { useCallback, useEffect, useState } from 'react';
import Particles from 'react-tsparticles';
import { loadSlim } from 'tsparticles-slim';
import type { Engine } from 'tsparticles-engine';

interface ParticlesBackgroundProps {
  color?: string[]; // 支持多色传入
}

export default function ParticlesBackground({ color }: ParticlesBackgroundProps) {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const darkMode = document.documentElement.classList.contains('dark');
    setIsDark(darkMode);
  }, []);

  const particlesInit = useCallback(async (engine: Engine) => {
    await loadSlim(engine);
  }, []);

  const fallbackColor = isDark ? ['#ffffff'] : ['#000000'];
  const particleColors = color && color.length > 0 ? color : fallbackColor;

  return (
    <Particles
      id="tsparticles"
      init={particlesInit}
      options={{
        fullScreen: { enable: true, zIndex: -1 },
        background: { color: { value: 'transparent' } },
        particles: {
          number: { value: 100 },
          color: { value: particleColors },
          links: {
            enable: true,
            color: particleColors[0],
            distance: 120,
            opacity: 0.4,
          },
          opacity: { value: 0.7 },
          size: { value: { min: 2, max: 4 } },
          move: { enable: true, speed: 1.2 },
        },
        detectRetina: true,
      }}
    />
  );
}
