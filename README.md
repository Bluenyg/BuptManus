# BuptManus

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

[English](./README.md) | [简体中文](./README_zh.md)

> Born from open source, giving back to open source

BUPTManus is a multi-agent AI automation framework built upon the excellent work of the open source community. Our goal is to combine language models with professional tools (such as web search, crawlers, and Python code execution) to create an automated general intelligence agent.

## Demo Video

- 📦 [Download Demo Video (MP4)](https://github.com/langmanus/langmanus/blob/main/assets/demo.mp4)

## Table of Contents
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Features](#features)
- [Installation & Setup](#installation--setup)
    - [Prerequisites](#prerequisites)
    - [Installation Steps](#installation-steps)
    - [Docker Deployment (**Optional: Cannot automate local browser or perform file system operations**)](#docker-deployment)
    - [Configuration](#configuration)
- [Backend Server](#backend-server)
- [Frontend Web Interface](#frontend-web-interface)
- [Development](#development)
- [Contributing](#contributing)
- [Acknowledgments](#acknowledgments)

## Quick Start

```bash
# Navigate to directory
cd BuptManus

# Create and activate virtual environment with uv
uv python install 3.12
uv venv --python 3.12

source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env file and fill in your API keys
```

### Browser Dependencies Installation

BuptManus supports multiple browser automation solutions, with Playwright recommended:

```bash
# Install Playwright browsers
playwright install

# Or install only Chromium (recommended)
playwright install chromium

# Verify installation
playwright --version

# Run the project
uv run main.py
```

## Architecture

BUPTManus implements a hierarchical multi-agent system with a supervisor agent coordinating specialized agents to complete complex tasks:

![BuptManus Architecture](assets/liuchengtu.png)

The system consists of the following agents working collaboratively:

1. **Coordinator**: Entry point for workflows, handles initial interactions and routes tasks
2. **Planner**: Analyzes tasks and formulates execution strategies
3. **Supervisor**: Oversees and manages execution of other agents
4. **Researcher**: Collects and analyzes information
5. **Coder**: Responsible for code generation and modification
6. **Browser**: Executes web browsing and information retrieval
7. **Reporter**: Generates reports and summaries of workflow results
8. **Life-Tool**: Provides life services such as weather queries and package tracking by calling tools in Mcp-Server, converting technical interfaces to natural language responses with strong extensibility

## Features

### Core Capabilities
- 🤖 **LLM Integration**
    - Support for open source models like Qwen
    - OpenAI-compatible API interface
    - Multi-layer LLM system adapted for different task complexities

### Tools and Integrations
- 🔍 **Search and Retrieval**
    - Web search through Tavily API
    - Neural search using Jina
    - Advanced content extraction

### Development Features
- 🐍 **Python Integration**
    - Built-in Python REPL
    - Code execution environment
    - Package management using uv

### Workflow Management
- 📊 **Visualization and Control**
    - Workflow diagram visualization
    - Multi-agent orchestration
    - Task allocation and monitoring

## Installation & Setup

### Prerequisites

- [uv](https://github.com/astral-sh/uv) package manager

### Installation Steps

BUPTManus uses [uv](https://github.com/astral-sh/uv) as a package manager to simplify dependency management.
Follow these steps to set up the virtual environment and install necessary dependencies:

```bash
# Step 1: Create and activate virtual environment with uv
uv python install 3.12
uv venv --python 3.12

# Unix/macOS:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate

# Step 2: Install project dependencies
uv sync

# Step 3: Install browser automation dependencies
playwright install
```

### Docker Deployment
- **Optional: Cannot automate local browser or perform file system operations**
- Using Docker allows quick deployment of BuptManus without manual environment configuration:

```bash
# Build Docker image
docker build -t buptmanus .

# Run container
docker run -d \
  --name buptmanus \
  -p 3000:3000 \
  -v $(pwd)/.env:/app/.env \
  buptmanus

# Or use docker-compose
docker-compose up -d
```

### Configuration

BUPTManus uses a three-tier LLM system for reasoning, basic tasks, and vision-language tasks respectively. Create a `.env` file in the project root and configure the following environment variables:

```ini
# Reasoning LLM Configuration (for complex reasoning tasks)
REASONING_MODEL=your_reasoning_model
REASONING_API_KEY=your_reasoning_api_key
REASONING_BASE_URL=your_custom_base_url  # Optional

# Basic LLM Configuration (for simple tasks)
BASIC_MODEL=your_basic_model
BASIC_API_KEY=your_basic_api_key
BASIC_BASE_URL=your_custom_base_url  # Optional

# Vision-Language LLM Configuration (for tasks involving images)
VL_MODEL=your_vl_model
VL_API_KEY=your_vl_api_key
VL_BASE_URL=your_custom_base_url  # Optional

# Tool API Keys
TAVILY_API_KEY=your_tavily_api_key
JINA_API_KEY=your_jina_api_key  # Optional

# Browser Configuration
CHROME_INSTANCE_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome  # Optional, Chrome executable path
```

> **Note:**
>
> - The system uses different models for different types of tasks:
>     - Reasoning LLM for complex decision-making and analysis
>     - Basic LLM for simple text tasks
>     - Vision-Language LLM for tasks involving image understanding
> - Base URLs for all LLMs can be customized independently
> - Each LLM can use different API keys
> - Jina API key is optional; providing your own key gives higher rate limits (you can get this key at [jina.ai](https://jina.ai/))
> - Tavily search is configured by default to return up to 5 results (you can get this key at [app.tavily.com](https://app.tavily.com/))

You can copy the `.env.example` file as a template to start:

```bash
cp .env.example .env
```

## Backend Server

### Basic Execution

Run BUPTManus with default settings:

```bash
uv run main.py
```

### API Server

BUPTManus provides a FastAPI-based API server with streaming response support:

```bash
# Start API server
make serve

# Or run directly
uv run server.py
```

The API server provides the following endpoints:

- `POST /api/chat/stream`: Chat endpoint for LangGraph calls with streaming response
    - Request body:
    ```json
    {
      "messages": [
        {"role": "user", "content": "Enter your query here"}
      ],  
      "debug": false
    }
    ```
    - Returns Server-Sent Events (SSE) stream containing agent responses

- `GET /api/chat/sessions`: Get all chat sessions for the user
    - Returns array of sessions with ID, title, creation time, etc.

- `POST /api/chat/sessions`: Create a new chat session
    - Request body:
    ```json
    {
      "title": "Optional session title"
    }
    ```

- `DELETE /api/chat/sessions/{session_id}`: Delete specified session and all its messages
    - Path parameter: `session_id` - ID of session to delete

- `GET /api/chat/sessions/{session_id}/messages`: Get all message history for specified session
    - Path parameter: `session_id` - Session ID
    - Returns array of messages sorted by time

### Advanced Configuration

BUPTManus can be customized through various configuration files in the `src/config` directory:
- `env.py`: Configure LLM models, API keys, and base URLs
- `tools.py`: Adjust tool-specific settings (such as Tavily search result limits)
- `agents.py`: Modify team composition and agent system prompts

### Agent Prompt System

BUPTManus uses a sophisticated prompt system in the `src/prompts` directory to define agent behaviors and responsibilities:

#### Core Agent Roles

- **Supervisor ([`src/prompts/supervisor.md`](src/prompts/supervisor.md))**: Coordinates the team and assigns tasks by analyzing requests and determining which expert should handle them. Responsible for deciding task completion and workflow transitions.

- **Researcher ([`src/prompts/researcher.md`](src/prompts/researcher.md))**: Specializes in gathering information through web search and data collection. Uses Tavily search and web crawling capabilities, avoiding mathematical calculations or file operations.

- **Coder ([`src/prompts/coder.md`](src/prompts/coder.md))**: Professional software engineer role focused on Python and bash scripting. Handles:
    - Python code execution and analysis
    - Shell command execution
    - Technical problem solving and implementation

- **File Manager ([`src/prompts/file_manager.md`](src/prompts/file_manager.md))**: Handles all file system operations with emphasis on proper formatting and saving of markdown content.

- **Browser ([`src/prompts/browser.md`](src/prompts/browser.md))**: Web interaction expert handling:
    - Website navigation
    - Page interactions (clicking, typing, scrolling)
    - Content extraction from web pages

- **Life-Tool ([`src/prompts/life_tool.md`](src/prompts/life_tools.md))**: Life service agent that provides weather queries, package tracking and other life services by calling tools in Mcp-Server, converting technical interfaces to natural language responses:

#### Prompt System Architecture

The prompt system uses a template engine ([`src/prompts/template.py`](src/prompts/template.py)) to:
- Load role-specific markdown templates
- Handle variable substitution (such as current time, team member information)
- Format system prompts for each agent

Each agent's prompts are defined in separate markdown files, allowing easy modification of behaviors and responsibilities without changing underlying code.

## Frontend Web Interface

### 🌌 BuptManus Web UI

BUPTManus provides a powerful Web user interface that offers an intuitive interactive experience for the multi-agent system.

### 🚀 Web Interface Features

- **Interactive Collapsible Sidebar**: Hover to expand for quick access to chat history, auto-collapse to keep workspace clean. Stays open when using search bar!
- **Instant History Search**: Real-time filtering of chat sessions in sidebar
- **Customizable UI**: Personalize experience through in-app settings menu, can change animated particle background colors
- **Safe and Intuitive Deletion**: Chat items show delete icon on hover with in-place confirmation dialog to prevent accidental deletion
- **User Guide**: One-time modal for new users introducing core features
- **Deep Thinking and Search Options**: Optional toggles to enhance LLM behavior
- **Multimodal Input**: Upload images and send text at once (supports Base64 encoded inline)
- **Dark Mode Toggle**: Instant light/dark switching using Tailwind `darkMode: 'class'`
- **Animated Particle Background**: Beautiful customizable background powered by `tsparticles`
- **Hot Reload Dev Server**: Via `pnpm dev`
- **Modern Tech Stack**: Built with **Next.js**, **TypeScript**, **Tailwind CSS**, and **Zustand** state management

### 🔧 Web Interface Prerequisites

- [BuptManus Core](https://github.com/Bluenyg/BuptManus)
- Node.js `v18+`
- `pnpm` `v8+`

### ⚙️ Web Interface Setup

```bash
# Enter web interface directory
cd webui

# Create environment configuration file
cp .env.example .env

# Open .env and configure
NEXT_PUBLIC_API_URL=http://localhost:3000/api
```

### 📦 Install and Start Web Interface

```bash
# Install dependencies
pnpm install

# Run project in development mode
pnpm dev
```

Then visit http://localhost:3000

### 🧪 Multimodal Support

You can now upload images combined with natural language text. Images are converted to Base64 format and transmitted as part of the message payload.

```json
{
  "type": "multimodal",
  "content": {
    "text": "What does this chart show?",
    "image": "data:image/png;base64,iVBORw0KGg..."
  }
}
```

## Development

BUPTManus provides a complete development environment and toolchain:

### Code Quality Tools
- Code linting: `make lint`
- Code formatting: `make format`

### Development Servers
- API server: `make serve`
- Web UI dev server: `pnpm dev` (in webui directory)

## Contributing

We welcome all forms of contributions! Whether fixing typos, improving documentation, or adding new features, your help is greatly appreciated. Please check our [Contributing Guide](CONTRIBUTING.md) to learn how to get started.

All contributions are welcome! From fixing typos to adding complete features — you're awesome!

## Acknowledgments

Special thanks to all open source projects and contributors that make BUPTManus possible. We stand on the shoulders of giants.

Heartfelt thanks to the open source community and all contributors. BUPTManus stands on the shoulders of giants. 🦾