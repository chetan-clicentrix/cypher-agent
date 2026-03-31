import asyncio
from typing import Optional, Dict, Any, List
from ..utils.logger import setup_logger
from .config import load_config
from ..ai.llm_router import LLMRouter
from ..ai.llm_orchestrator import LLMOrchestrator
from ..ai.tts_orchestrator import TTSOrchestrator
from ..ai.stt_orchestrator import STTOrchestrator
from ..ai.wake_word_detector import WakeWordDetector
from ..agents.agent_router import AgentRouter
from ..agents.system import SystemAgent
from ..agents.general import GeneralAgent
from ..agents.memory import MemoryAgent
from ..agents.learning import LearningAgent
from ..agents.voice import VoiceAgent
from ..agents.knowledge import KnowledgeAgent
from ..agents.research import ResearchAgent
from ..utils.memory import get_memory

class CypherEngine:
    """Main orchestration engine for Cypher AI Assistant"""
    
    def __init__(self):
        self.config = load_config()
        self.logger = setup_logger(self.config.app.log_level)
        self.logger.info(f"🚀 Initializing {self.config.app.name} v{self.config.app.version}")
        
        # Initialize AI components
        self.llm_router = LLMRouter(self.config.llm_routing.model_dump())
        self.llm_orchestrator = LLMOrchestrator()
        
        # Initialize TTS system
        self.tts_orchestrator = TTSOrchestrator()
        
        # Initialize STT system
        self.stt_orchestrator = STTOrchestrator()
        
        # Initialize memory system
        self.memory = get_memory()
        
        # SESSION INITIALIZATION PROTOCOL (like OpenClaw)
        self._initialize_session()
        
        # Initialize agents (pass llm_router to general agent for intelligent routing)
        self.system_agent = SystemAgent(self.llm_orchestrator)
        self.memory_agent = MemoryAgent(self.llm_orchestrator)
        self.general_agent = GeneralAgent(self.llm_orchestrator, self.llm_router)
        self.learning_agent = LearningAgent(self.llm_orchestrator, self.llm_router)
        self.voice_agent = VoiceAgent(self.llm_orchestrator, self.tts_orchestrator)
        self.knowledge_agent = KnowledgeAgent(self.llm_orchestrator)
        self.research_agent = ResearchAgent(self.llm_orchestrator)
        
        # Initialize agent router with specialized agents and LLM capability
        self.agent_router = AgentRouter(
            agents=[
                self.system_agent, 
                self.memory_agent,
                self.voice_agent,
                self.knowledge_agent,
                self.research_agent
            ],
            fallback_agent=self.general_agent,
            llm_orchestrator=self.llm_orchestrator
        )
        
        self.logger.info("✅ Cypher is ready!")
        
        # Wake word detector (initialized but not started yet)
        self.wake_detector: WakeWordDetector = None
        self._voice_mode_event = asyncio.Event()
    
    def _initialize_session(self):
        """
        Session initialization protocol (inspired by OpenClaw)
        Loads all memory at startup for context awareness
        """
        self.logger.info("📖 Loading session context...")
        
        # Context is already loaded by Memory.__init__(), just log it
        user_name = self.memory.user_profile.get('name', 'Unknown')
        memory_entries = len(self.memory.long_term_memory)
        
        self.logger.info(f"   ✓ SOUL.md loaded ({len(self.memory.soul_content)} chars)")
        self.logger.info(f"   ✓ USER.md loaded (User: {user_name})")
        self.logger.info(f"   ✓ MEMORY.md loaded ({memory_entries} entries)")
        self.logger.info(f"   ✓ Today's log ready")
    
    def _strip_for_tts(self, text: str) -> str:
        """
        Clean text before sending to TTS.
        Removes markdown, emojis, and symbols that sound bad when spoken.
        """
        import re
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)       # **bold**
        text = re.sub(r'\*(.*?)\*', r'\1', text)            # *italic*
        text = re.sub(r'`{1,3}[^`]*`{1,3}', '', text)      # `code` or ```block```
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # # Headers
        text = re.sub(r'^[-•*]\s+', '', text, flags=re.MULTILINE)   # - bullets
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)       # [links](url)
        # Remove emojis
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        # Remove multiple spaces/newlines
        text = re.sub(r'\n+', '. ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    async def process_query(self, query: str) -> str:
        """Process a user query through the agent system"""
        
        # Route query to appropriate agent and get response
        self.logger.info(f"📋 Processing query: '{query[:50]}...'")
        response = await self.agent_router.process_query(query)
        
        # Run learning agent in background to extract knowledge
        try:
            await self.learning_agent.process(query, context={'response': response})
        except Exception as e:
            self.logger.error(f"Learning agent error: {e}")
        
        # Auto-speak response if voice is enabled
        if self.voice_agent.voice_enabled:
            try:
                # Strip markdown before speaking - TTS should sound natural
                speak_text = self._strip_for_tts(response)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self.tts_orchestrator.speak,
                    speak_text
                )
            except Exception as e:
                self.logger.error(f"TTS error: {e}")
        
        return response
    
    async def run_interactive(self, initial_query: Optional[str] = None):
        """Run interactive CLI (text) mode"""
        stt_available = self.stt_orchestrator.is_available()
        hint = "(type or say 'voice' to speak)" if stt_available else "(type your message)"
        
        self.logger.info(f"💬 Interactive mode started. Type 'exit' to quit. {hint}")
        self.logger.info("=" * 60)
        
        # If we have an initial query from the menu selection, process it first
        if initial_query:
            response = await self.process_query(initial_query)
            print(f"\n🤖 Cipher: {response}")
        
        while True:
            try:
                query = input("\n🔮 You: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['exit', 'quit', 'bye']:
                    self.logger.info("👋 Goodbye!")
                    break
                
                if query.lower() in ['voice mode', 'start voice', 'talk mode', 'cipher']:
                    await self.run_voice_mode()
                    break
                
                # Switch to Gemini Live mode
                if query.lower() in ['jarvis', 'gemini live', 'live mode']:
                    await self.run_gemini_live()
                    break
                
                # Single voice input
                if query.lower() in ['voice', '!', 'listen'] and stt_available:
                    print("🎙️ Listening... speak now!")
                    spoken_query = await self.stt_orchestrator.listen_async()
                    if spoken_query:
                        print(f"📝 You said: {spoken_query}")
                        query = spoken_query
                    else:
                        print("❌ Could not hear anything. Please try again.")
                        continue
                
                response = await self.process_query(query)
                print(f"\n🤖 Cypher: {response}")
                
            except KeyboardInterrupt:
                self.logger.info("\n👋 Goodbye!")
                break
            except Exception as e:
                self.logger.error(f"❌ Error: {e}")
    
    async def run_voice_mode(self, from_wake_word: bool = False):
        """
        Full voice conversation mode - continuous listen + speak loop
        """
        if not self.stt_orchestrator.is_available():
            print("❌ STT not available. Cannot enter voice mode.")
            return
        
        # Auto-enable TTS for voice mode
        self.voice_agent.voice_enabled = True
        
        print("\n" + "=" * 50)
        print("  🎙️  VOICE MODE ACTIVE")
        print("  Speak to Cipher — it will listen and talk back")
        print("  Say 'stop', 'exit', or 'goodbye' to quit")
        print("=" * 50 + "\n")
        
        # Greeting
        greeting = f"Voice mode activated! Hello Chetan, I'm listening. How can I help you?"
        print(f"🤖 Cipher: {greeting}")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.tts_orchestrator.speak, greeting)
        
        # ANTI-ECHO DELAY: Wait for greeting to finish resonating
        await asyncio.sleep(1.0)
        
        stop_words = ['stop', 'exit', 'goodbye', 'bye', 'quit', 'stop listening']
        
        while True:
            try:
                print("\n🎙️ Listening...")
                
                # Listen for speech
                spoken_query = await self.stt_orchestrator.listen_async()
                
                if not spoken_query:
                    # No speech - try again
                    print("(No speech detected, still listening...)")
                    continue
                
                print(f"🗣️  You: {spoken_query}")
                spoken_lower = spoken_query.lower()
                
                # Check for stop command - robust matching
                # Handles STT mishearings too (stop → top, bye → buy, etc.)
                is_stop = any(word in spoken_lower for word in stop_words)
                is_stop_partial = any(
                    word in spoken_lower 
                    for word in ['stop', 'bye', 'exit', 'quit', 'goodbye', 'good bye', 
                                 'that\'s all', 'thats all', 'no more', 'sleep now',
                                 'go to sleep', 'enough']
                )
                
                if is_stop or is_stop_partial:
                    farewell = "Got it! Say 'Cipher' anytime to wake me up again." if from_wake_word else "Goodbye! Switching back to text mode."
                    print(f"🤖 Cipher: {farewell}")
                    await loop.run_in_executor(None, self.tts_orchestrator.speak, farewell)
                    self.voice_agent.voice_enabled = False
                    if not from_wake_word:
                        print("\n" + "=" * 50)
                        print("  💬  Back to text mode")
                        print("=" * 50 + "\n")
                    break
                
                # Process and respond
                response = await self.process_query(spoken_query)
                print(f"🤖 Cipher: {response}\n")
                
                # ANTI-ECHO DELAY: Wait for room audio to physically finish playing
                # and reflections to die down before re-opening the STT microphone.
                # If we don't do this, the STT calibrates its ambient noise floor
                # to the trailing echo of the TTS voice, causing deafness.
                await asyncio.sleep(1.0)
                
                
            except KeyboardInterrupt:
                print("\n👋 Exiting voice mode...")
                self.voice_agent.voice_enabled = False
                break
            except Exception as e:
                self.logger.error(f"Voice mode error: {e}")
                continue
    
    async def run_gemini_live(self):
        """
        Runs the Gemini Live WebSocket agent.
        """
        from ..agents.voice.gemini_live_agent import GeminiLiveAgent
        import traceback
        
        print("\n" + "=" * 50)
        print("  🎙️  JARVIS MULTIMODAL LIVE ACTIVE")
        print("  Speak to Jarvis naturally. Interrupt at any time.")
        print("  Say 'stop', 'exit', or 'goodbye' to quit")
        print("=" * 50 + "\n")
        
        agent = GeminiLiveAgent()
        try:
            # Run the Gemini agent in a separate thread.
            # This isolates its internal asyncio task cancellation (used during shutdown)
            # from crashing the main wake-word standby loop.
            loop = asyncio.get_event_loop()
            
            # The agent itself is mostly async, so we need to run it in a new event loop 
            # within a dedicated background thread.
            def _run_agent_sync():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(agent.run())
                except Exception as e:
                    pass  # Suppress internal agent shutdown errors
                finally:
                    new_loop.close()
                
            await loop.run_in_executor(None, _run_agent_sync)
            
        except asyncio.CancelledError:
            self.logger.info("Gemini Live task gracefully cancelled")
        except Exception as e:
            self.logger.error(f"Gemini Live mode error: {e}")
            traceback.print_exc()
        
        print("\n" + "=" * 50)
        print("  💬  Back to text mode")
        print("=" * 50 + "\n")
    
    async def run_wake_word_mode(self):
        """
        Always-on wake word mode.
        Cipher runs silently in background, listening for 'Cipher'.
        When wake word detected → enters voice conversation → goes back to sleep.
        """
        if not self.stt_orchestrator.is_available():
            print("❌ STT not available. Cannot enter wake word mode.")
            return
        
        user_name = self.memory.user_profile.get('name', 'Chetan')
        
        print("\n" + "=" * 50)
        print("  🌙  CIPHER IS NOW IN STANDBY")
        print(f"  Say 'Cipher' to wake up Modular Mode")
        print(f"  Say 'Jarvis' to wake up Gemini Live Mode")
        print("  Press Ctrl+C to exit")
        print("=" * 50 + "\n")
        
        # Announce readiness via TTS
        ready_msg = f"I'm standing by. Say Cipher or Jarvis to wake me up."
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.tts_orchestrator.speak, ready_msg)
        
        # Create wake word detector
        wake_triggered = asyncio.Event()
        self.wake_entity = "cipher"
        
        def on_wake(entity):
            """Called when wake word detected - triggers voice mode"""
            self.wake_entity = entity
            loop.call_soon_threadsafe(wake_triggered.set)
        
        self.wake_detector = WakeWordDetector(on_wake=on_wake)
        self.wake_detector.start()
        
        try:
            while True:
                print("👂 Listening for wake word 'Cipher' or 'Jarvis'...")
                
                # Wait for wake word
                wake_triggered.clear()
                try:
                    await wake_triggered.wait()
                except asyncio.CancelledError:
                    break
                
                # Wake up!
                self.wake_detector.pause()
                
                print(f"\n🔔 Wake word detected! Entity: {self.wake_entity}")
                
                if self.wake_entity == "jarvis":
                    print("🤖 Starting Gemini Live Mode...")
                    await self.run_gemini_live()
                else:
                    wake_msg = f"Hey {user_name}, I'm listening!"
                    print(f"🤖 Cipher: {wake_msg}")
                    await loop.run_in_executor(None, self.tts_orchestrator.speak, wake_msg)
                    
                    # Enter voice conversation
                    await self.run_voice_mode(from_wake_word=True)
                
                # Resume wake word detection
                print("\n🌙 Going back to standby... say 'Cipher' or 'Jarvis' to wake up again")
                wake_triggered.clear()  # Flush any remaining echo triggers to prevent double-waking 
                self.wake_detector.resume()
                
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n👋 Cipher shutting down...")
            if self.wake_detector:
                self.wake_detector.stop()
    
    def run_headless(self):
        """
        Headless entry point for the 24/7 background service.
        Skips the interactive menu and goes straight to always-on wake-word mode.
        Called by service/cipher_service.py.
        """
        self.logger.info("🌙 Headless service mode — entering wake-word standby")
        asyncio.run(self.run_wake_word_mode())

    def run(self):
        """Main entry point with mode selection"""
        self.logger.info("📋 Phase 1: LLM Integration complete!")
        self.logger.info("🔮 Starting interactive mode...")
        
        print("\n" + "=" * 50)
        print("  🔮  How would you like to use Cipher?")
        print()
        print("  [1] 💬 Chat mode   — type messages")
        print("  [2] 🎙️  Voice mode  — press enter, then speak")
        print("  [3] 🌙 Always-on   — say 'Cipher' or 'Jarvis' to wake up")
        print("=" * 50)
        
        choice = input("  Choose (1/2/3, default=3): ").strip()
        
        if choice == "1":
            asyncio.run(self.run_interactive())
        elif choice == "2":
            asyncio.run(self.run_voice_mode())
        elif choice in ["3", ""]:
            # Default: always-on wake word mode!
            asyncio.run(self.run_wake_word_mode())
        else:
            # Fallback: user typed a query instead of a selection!
            print(f"\n🚀 Processing raw query: {choice}")
            asyncio.run(self.run_interactive(initial_query=choice))

if __name__ == "__main__":
    engine = CypherEngine()
    engine.run()
