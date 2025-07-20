'use client';

import { useEffect, useState } from 'react';

export default function DarkModeToggle() {
  const [isDark, setIsDark] = useState(false);

  // 自动读取系统或localStorage的主题偏好
  useEffect(() => {
    const darkPref = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (darkPref === 'dark' || (!darkPref && systemPrefersDark)) {
      document.documentElement.classList.add('dark');
      setIsDark(true);
    } else {
      document.documentElement.classList.remove('dark');
      setIsDark(false);
    }
  }, []);

  const toggleDarkMode = () => {
    const newTheme = isDark ? 'light' : 'dark';
    localStorage.setItem('theme', newTheme);
    document.documentElement.classList.toggle('dark');
    setIsDark(!isDark);
  };

  return (
    <button
      onClick={toggleDarkMode}
      className="
        fixed top-3 right-3 z-50
        h-8 w-8
        flex items-center justify-center
        rounded-full
        bg-white/30 dark:bg-black/30
        text-lg
        backdrop-blur-sm
        shadow-md
        hover:bg-white/50 dark:hover:bg-black/50
        transition-all duration-300
      "
      aria-label="Toggle Dark Mode"
    >
      {isDark ? '🌞' : '🌙'}
    </button>
  );
}
