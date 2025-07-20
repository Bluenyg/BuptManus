# 🌌 LangManus Web UI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> From Open Source, For Open Intelligence

**The official web UI for [LangManus](https://github.com/langmanus/langmanus)** — a community-driven AI automation framework combining large language models with tool orchestration, image understanding, and more.

---

## 🚀 Features

- ✨ **Multimodal input**: Upload images and send text in one go (Base64-encoded inline support)
- 🌙 **Dark Mode toggle**: Instant light/dark switching with Tailwind `darkMode: 'class'`
- 🎇 **Particle background**: Beautiful animated background powered by `tsparticles`
- 🧠 **Deep Thinking & Search Options**: Optional toggles for enhanced LLM behavior
- ⚡ **Hot-reload dev server** with `pnpm dev`
- 💅 Built with **Next.js**, **TypeScript**, **Tailwind CSS**

---

## 📺 Demo

- ▶️ [Watch Demo on YouTube](https://youtu.be/sZCHqrQBUGk)
- 📦 [Download Demo Video (MP4)](https://github.com/langmanus/langmanus/blob/main/assets/demo.mp4)

---

## 📦 Quick Start

### 🔧 Prerequisites

- [LangManus Core](https://github.com/langmanus/langmanus)
- Node.js `v18+`
- `pnpm` `v8+`

### ⚙️ Setup

```bash
# Clone the project
git clone https://github.com/langmanus/langmanus-web.git
cd langmanus-web

# Create your env file
cp .env.example .env

#Open .env and set
NEXT_PUBLIC_API_URL=http://localhost:3000
```

### 📦 Install & Launch
```bash
pnpm install
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

### 📄 License
This project is licensed under the MIT License.

### 🙏 Acknowledgments
Huge thanks to the open source community and all contributors.
LangManus stands on the shoulders of giants. 🦾