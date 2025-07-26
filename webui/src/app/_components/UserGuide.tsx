'use client';

import { useEffect, useState } from 'react';

export function UserGuide() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const hasSeenGuide = localStorage.getItem('BuptManus.userGuideShown');
    if (!hasSeenGuide) {
      setVisible(true);
    }
  }, []);

  const handleClose = () => {
    setVisible(false);
    localStorage.setItem('BuptManus.userGuideShown', 'true');
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-24 left-4 md:left-8 z-50 bg-white dark:bg-gray-800 text-gray-800 dark:text-white border rounded-lg shadow-lg p-4 w-72">
      <h3 className="font-semibold mb-2">👋 Welcome to use BuptManus！</h3>
      <ul className="list-disc pl-5 text-sm space-y-1">
        <li>🌗 Click on the top right corner to switch between light and dark mode.</li>
        <li>🎨 Click the button in the top left corner to change the color of the particles.</li>
        <li>🖼️ Upload images to experience multimodal input.</li>
      </ul>
      <button
        onClick={handleClose}
        className="mt-4 px-3 py-1 rounded bg-blue-500 text-white text-sm hover:bg-blue-600"
      >
        I know.
      </button>
    </div>
  );
}
