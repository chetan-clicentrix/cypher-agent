# Cypher AI Assistant

Your intelligent AI assistant for development and daily tasks.

## 🚀 Quick Start

### 1. Activate Virtual Environment
```bash
venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.template .env
# Edit .env and add your API keys
```

#### Sample `.env` Configuration:
```env
# Essential for Wake Word
PICOVOICE_API_KEY=your_key_here

# Recommended for Gemini Live Mode
GOOGLE_API_KEY=your_key_here

# For STT and Enhanced LLM Skills
NVIDIA_API_KEY=your_key_here

# Optional: Tavily, Anthropic, OpenAI
TAVILY_API_KEY=your_key_here
```

### 4. Run Cypher
```bash
python -m src.core.engine
```

## 📁 Project Structure

```
cypher-ai-assistant/
├── venv/                   # Virtual environment
├── src/
│   ├── core/              # Core engine and config
│   ├── utils/             # Utilities (logger, etc.)
│   ├── ai/                # LLM integration (Phase 1)
│   ├── tools/             # Tool implementations (Phase 2+)
│   └── voice/             # Voice interface (Phase 3)
├── config/                # Configuration files
├── tests/                 # Unit tests
├── data/logs/             # Application logs
└── requirements.txt       # Dependencies
```

## 🎯 Development Status

- [x] Phase 0: Foundation Setup ✅
- [ ] Phase 1: Core Infrastructure (LLM integration)
- [ ] Phase 2: Essential Tools
- [ ] Phase 3: Voice Interface
- [ ] Phase 4: Advanced Integration
- [ ] Phase 5: Intelligence & Memory
- [ ] Phase 6: DevOps & Security
- [ ] Phase 7: Polish & UX

## 🛠️ Tech Stack

- **Python**: 3.11+
- **AI Framework**: LangChain (Phase 1)
- **Local LLM**: Ollama (Phase 1)
- **Cloud LLM**: OpenAI GPT-4, Anthropic Claude
- **Vector DB**: ChromaDB (Phase 5)
- **Voice**: Whisper, Porcupine (Phase 3)

## 📝 Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Test the foundation: `python -m src.core.engine`
3. Proceed to Phase 1: LLM integration

---

## ⚡ Core Capabilities & Intelligent Modes

We are building a versatile agent capable of executing complex instructions dynamically.

### 🧠 Advanced Interaction
- **Gemini Live Mode**: Features real-time, continuous voice and text interaction powered by Google Gemini for lightning-fast responses.
- **Dynamic Memory**: Engages in context-aware interactions utilizing long-term structured memory and personalized user profiling.

### 🔧 System Integration
- **PC Control Tools**: Seamlessly control underlying system functions including volume, power states, rich media playback, and hardware monitoring.
- **Application Management**: Launch, monitor, and manage local applications entirely through natural language processing.
- **Vision & Hand Tracking**: Equipped with advanced gesture recognition and visual inputs to facilitate completely hands-free control.

### 🔮 Upcoming Features
- **Smart Home Automation**: Future updates will introduce capabilities for controlling smart home IoT devices (lights, thermostats, security systems) directly through the assistant's unified interface.
