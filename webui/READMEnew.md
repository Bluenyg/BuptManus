# 🌌 BuptManus Web UI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> From Open Source, For Open Intelligence

**The official web UI for [BuptManus](https://github.com/Bluenyg/BuptManus)** — a general-purpose AI agent based on a multi-agent architecture, integrating large language models with tool orchestration, image understanding, and more — collaboratively driven by the open community.

---

## 🚀 Features

- ✨ **Interactive & Collapsible Sidebar**: Hover to expand for quick access to your chat history, and it collapses automatically for a clean workspace. It even stays open when you're using the search bar!
- 🔍 **Instant History Search**: Filter your chat sessions in real-time directly within the sidebar.
- 🎨 **Customizable UI**: Personalize your experience by changing the animated particle background colors through the in-app settings menu.
- 🛡️ **Safe & Intuitive Deletion**: Hover-to-reveal delete icons on chat items with an in-place confirmation dialog to prevent accidental deletion.
- 👋 **Helpful User Guide**: A welcoming, one-time modal guides new users through the core features.
- 🧠 **Deep Thinking & Search Options**: Optional toggles for enhanced LLM behavior.
- 🖼️ **Multimodal Input**: Upload images and send text in one go (Base64-encoded inline support).
- 🌙 **Dark Mode Toggle**: Instant light/dark switching with Tailwind `darkMode: 'class'`.
- 🎇 **Animated Particle Background**: Beautiful and customizable background powered by `tsparticles`.
- ⚡ **Hot-reload dev server** with `pnpm dev`.
- 💅 Built with **Next.js**, **TypeScript**, **Tailwind CSS**, and **Zustand** for state management.

---

## 📺 Demo

- ▶️ [Watch Demo on YouTube](https://youtu.be/sZCHqrQBUGk)
- 📦 [Download Demo Video (MP4)](https://github.com/langmanus/langmanus/blob/main/assets/demo.mp4)

---

## 📦 Quick Start

### 🔧 Prerequisites

- [BuptManus Core](https://github.com/Bluenyg/BuptManus)
- Node.js `v18+`
- `pnpm` `v8+`

### ⚙️ Setup

```bash
#
cd webui

# Create your env file
cp .env.example .env

#Open .env and set
NEXT_PUBLIC_API_URL=http://localhost:3000
```

### 📦 Install & Launch
```bash
# Install dependencies
pnpm install

# Run the project in development mode
pnpm dev
```
Then visit http://localhost:3000

### 🧪 Multi-Modal Support
You can now upload images and combine them with natural language text. Images are converted to Base64 and transmitted as part of the message payload.
```json
{
  "type": "multimodal",
  "content": {
    "text": "What does this chart show?",
    "image": "data:image/png;base64,iVBORw0KGg..."
  }
}
```

### 🤝 Contributing
All contributions are welcome!
From fixing typos to adding full features — you're awesome!

See CONTRIBUTING.md for how to get involved.

### 🙏 Acknowledgments
Huge thanks to the open source community and all contributors.
BuptManus stands on the shoulders of giants. 🦾