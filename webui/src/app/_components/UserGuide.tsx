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
    // Background overlay
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm">
      {/* Guide content card */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-md w-full m-4 p-6 border dark:border-gray-700">

        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
          👋 Welcome to BuptManus!
        </h2>

        <p className="text-gray-600 dark:text-gray-300 mb-6">
          Here are a few tips on core features to get you started:
        </p>

        <ul className="space-y-4 text-gray-700 dark:text-gray-200">
          <li className="flex items-start">
            <span className="text-xl mr-4">🌗</span>
            <div>
              <span className="font-semibold">Switch Themes</span>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Click on the top right corner to switch between light and dark modes.
              </p>
            </div>
          </li>

          <li className="flex items-start">
            <span className="text-xl mr-4">🎨</span>
            <div>
              <span className="font-semibold">Customize Particle Colors</span>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Click the button in the top left corner, you can freely change the color of the background particles.
              </p>
            </div>
          </li>

          <li className="flex items-start">
            <span className="text-xl mr-4">🖼️</span>
            <div>
              <span className="font-semibold">Multimodal Input</span>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Click the add button next to the input box to upload an image for multimodal interaction.
              </p>
            </div>
          </li>
        </ul>

        {/* Confirmation Button */}
        <div className="mt-8 text-center">
          <button
            onClick={handleClose}
            className="bg-blue-600 text-white font-semibold py-2 px-6 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition-colors"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}

