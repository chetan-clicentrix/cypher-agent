"""
Gemini Live Voice Agent — "Jarvis"

A real-time, low-latency voice agent that:
1. Streams microphone audio to Gemini's Multimodal Live API via WebSocket
2. Plays streamed audio from Gemini back through the speaker
3. Handles function/tool calls from Gemini so Jarvis can search the web,
   read files, check system stats, and recall personal memory
"""

import asyncio
import json
import logging
import os
import queue
import threading
import time
import traceback
import pyaudio
from pathlib import Path
from google import genai
from google.genai import types

# Suppress the harmless "non-data parts" SDK warning (audio + text transcript is normal)
logging.getLogger("google_genai.live").setLevel(logging.ERROR)


# ──────────────────────────────────────────────
# Tool Implementation Functions (run locally)
# ──────────────────────────────────────────────

def _tool_search_web(query: str) -> str:
    """Run DuckDuckGo web search and return summarised results."""
    try:
        from src.tools.web_search import search_web, search_tavily
        import os
        # Use Tavily if key available, otherwise DuckDuckGo
        if os.getenv("TAVILY_API_KEY"):
            results = search_tavily(query, max_results=5)
        else:
            results = search_web(query, max_results=5)
        if not results:
            return "No results found."
        lines = []
        for r in results[:5]:
            title = r.get("title", "")
            body = r.get("body", r.get("content", ""))[:300]
            lines.append(f"**{title}**: {body}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"


def _tool_read_file(file_path: str) -> str:
    """Read a local file and return its content."""
    try:
        from src.tools.file_reader import read_file_content
        result = read_file_content(file_path)
        if result.get("success"):
            content = result["content"]
            if result.get("truncated"):
                content += "\n\n[File truncated for length]"
            return content
        return f"Error reading file: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"File read error: {e}"


def _tool_list_files(directory: str, pattern: str = "*") -> str:
    """List files in a local directory."""
    try:
        from src.tools.file_search import list_files
        files = list_files(directory, pattern=pattern)
        if not files:
            return f"No files found in '{directory}' matching '{pattern}'"
        return "\n".join(files[:50])
    except Exception as e:
        return f"File list error: {e}"


def _tool_get_system_stats() -> str:
    """Get current CPU, RAM, and disk usage."""
    try:
        from src.tools.system_monitor import SystemMonitor
        mon = SystemMonitor()
        cpu = mon.get_cpu_usage()
        mem = mon.get_memory_usage()
        disk = mon.get_disk_usage()
        return (
            f"CPU: {cpu['overall']}% ({cpu['count']} cores)\n"
            f"RAM: {mem['used_gb']}GB used / {mem['total_gb']}GB total ({mem['percent']}%)\n"
            f"Disk C:\\: {disk['used_gb']}GB used / {disk['total_gb']}GB total ({disk['percent']}%)"
        )
    except Exception as e:
        return f"System monitor error: {e}"


def _tool_read_memory() -> str:
    """Read Cipher's personal memory about the user (MEMORY.md)."""
    try:
        memory_path = Path("MEMORY.md")
        if memory_path.exists():
            return memory_path.read_text(encoding="utf-8")[:3000]
        return "No memory file found."
    except Exception as e:
        return f"Memory read error: {e}"


def _tool_get_battery_status() -> str:
    """Get battery charge level, charging status, and time remaining."""
    try:
        from src.tools.system_monitor import SystemMonitor
        mon = SystemMonitor()
        b = mon.get_battery_status()
        if "error" in b:
            return b["error"]
        return (
            f"Battery: {b['percent']}% — {b['status']}\n"
            f"Time: {b['time_info']}\n"
            f"Health: {b['health']}"
        )
    except Exception as e:
        return f"Battery check error: {e}"


# ──────────────────────────────────────────────
# Tool Dispatcher
# ──────────────────────────────────────────────

# Import PC control tools
from src.tools.pc_control import (
    play_on_youtube, open_url, open_app, open_folder,
    set_volume, mute_volume, take_screenshot,
    create_note, read_notes, set_reminder, system_control
)
# Import Hand control tools
from src.tools.hand_control import start_hand_tracking, stop_hand_tracking

TOOL_HANDLERS = {
    # Info tools
    "search_web":         lambda args: _tool_search_web(args.get("query", "")),
    "read_file":          lambda args: _tool_read_file(args.get("file_path", "")),
    "list_files":         lambda args: _tool_list_files(args.get("directory", "."), args.get("pattern", "*")),
    "get_system_stats":   lambda args: _tool_get_system_stats(),
    "get_battery_status": lambda args: _tool_get_battery_status(),
    "read_memory":        lambda args: _tool_read_memory(),
    # PC control tools
    "play_on_youtube":    lambda args: play_on_youtube(args.get("query", "")),
    "open_url":           lambda args: open_url(args.get("url", "")),
    "open_app":           lambda args: open_app(args.get("app_name", "")),
    "open_folder":        lambda args: open_folder(args.get("folder_path", ".")),
    "set_volume":         lambda args: set_volume(args.get("level", 50)),
    "mute_volume":        lambda args: mute_volume(),
    "take_screenshot":    lambda args: take_screenshot(),
    "create_note":        lambda args: create_note(args.get("text", "")),
    "read_notes":         lambda args: read_notes(int(args.get("last_n", 10))),
    "set_reminder":       lambda args: set_reminder(args.get("minutes", 5), args.get("message", "Reminder")),
    "system_control":     lambda args: system_control(args.get("action", "")),
    # Hand Tracking
    "start_hand_tracking": lambda args: start_hand_tracking(),
    "stop_hand_tracking":  lambda args: stop_hand_tracking(),
    # Session
    "exit_session":       lambda args: "__EXIT__",
}


# ──────────────────────────────────────────────
# Gemini Tool Declaration Schema
# ──────────────────────────────────────────────

def _build_tools() -> list:
    return [
        types.Tool(function_declarations=[

            # ── Info Tools ──────────────────────────────────
            types.FunctionDeclaration(
                name="read_file",
                description="Read the content of a local file on the user's computer.",
                parameters=types.Schema(type="OBJECT", properties={
                    "file_path": types.Schema(type="STRING", description="Absolute or relative path to the file.")
                }, required=["file_path"])
            ),
            types.FunctionDeclaration(
                name="list_files",
                description="List files in a directory on the user's computer.",
                parameters=types.Schema(type="OBJECT", properties={
                    "directory": types.Schema(type="STRING", description="Directory path to list."),
                    "pattern": types.Schema(type="STRING", description="File glob pattern, e.g. '*.py'.")
                }, required=["directory"])
            ),
            types.FunctionDeclaration(
                name="get_system_stats",
                description="Get current CPU usage, RAM usage, and disk usage of the user's computer.",
            ),
            types.FunctionDeclaration(
                name="get_battery_status",
                description="Get the laptop's battery percentage, charging status, time remaining, and health.",
            ),
            types.FunctionDeclaration(
                name="read_memory",
                description="Read the personal memory file about the user (name, preferences, goals).",
            ),

            # ── Media & Browser ─────────────────────────────
            types.FunctionDeclaration(
                name="play_on_youtube",
                description="Search YouTube for a song, video, or topic and open it in the browser.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": types.Schema(type="STRING", description="What to search for on YouTube.")
                }, required=["query"])
            ),
            types.FunctionDeclaration(
                name="open_url",
                description="Open any website URL in the default browser.",
                parameters=types.Schema(type="OBJECT", properties={
                    "url": types.Schema(type="STRING", description="Full URL to open, e.g. https://google.com")
                }, required=["url"])
            ),

            # ── App & Folder Control ─────────────────────────
            types.FunctionDeclaration(
                name="open_app",
                description="Open a Windows application by name, such as Chrome, VS Code, Spotify, Notepad, WhatsApp, etc.",
                parameters=types.Schema(type="OBJECT", properties={
                    "app_name": types.Schema(type="STRING", description="Name of the app to open, e.g. 'chrome', 'vs code', 'spotify'.")
                }, required=["app_name"])
            ),
            types.FunctionDeclaration(
                name="open_folder",
                description="Open a folder in Windows Explorer.",
                parameters=types.Schema(type="OBJECT", properties={
                    "folder_path": types.Schema(type="STRING", description="Path to the folder to open.")
                }, required=["folder_path"])
            ),

            # ── Volume ──────────────────────────────────────
            types.FunctionDeclaration(
                name="set_volume",
                description="Set the system volume to a specific level between 0 and 100.",
                parameters=types.Schema(type="OBJECT", properties={
                    "level": types.Schema(type="INTEGER", description="Volume level from 0 (mute) to 100 (max).")
                }, required=["level"])
            ),
            types.FunctionDeclaration(
                name="mute_volume",
                description="Toggle mute/unmute on the system volume.",
            ),

            # ── Screenshot ──────────────────────────────────
            types.FunctionDeclaration(
                name="take_screenshot",
                description="Take a screenshot of the current screen and save it to the Desktop.",
            ),

            # ── Notes ───────────────────────────────────────
            types.FunctionDeclaration(
                name="create_note",
                description="Save a note or reminder text to the notes file with a timestamp.",
                parameters=types.Schema(type="OBJECT", properties={
                    "text": types.Schema(type="STRING", description="The note content to save.")
                }, required=["text"])
            ),
            types.FunctionDeclaration(
                name="read_notes",
                description="Read the most recent saved notes.",
                parameters=types.Schema(type="OBJECT", properties={
                    "last_n": types.Schema(type="INTEGER", description="Number of recent notes to show. Default 10.")
                })
            ),

            # ── Reminders ───────────────────────────────────
            types.FunctionDeclaration(
                name="set_reminder",
                description="Set a reminder that fires a Windows notification after a number of minutes.",
                parameters=types.Schema(type="OBJECT", properties={
                    "minutes": types.Schema(type="NUMBER", description="How many minutes until the reminder fires."),
                    "message": types.Schema(type="STRING", description="The reminder message.")
                }, required=["minutes", "message"])
            ),

            # ── System Power ─────────────────────────────────
            types.FunctionDeclaration(
                name="system_control",
                description="Control system power: sleep, shutdown, restart, lock, or cancel a pending shutdown.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": types.Schema(type="STRING", description="One of: sleep, shutdown, restart, lock, cancel.")
                }, required=["action"])
            ),

            # ── Session ──────────────────────────────────────
            types.FunctionDeclaration(
                name="exit_session",
                description="End the voice session and return to text mode. Call when the user says goodbye or stop.",
            ),
            # ── Hand Tracking ─────────────────────────────────
            types.FunctionDeclaration(
                name="start_hand_tracking",
                description="Turn on hand tracking mode, allowing the user to control their PC with hand gestures via their camera. MUST BE called explicitly when user asks for it.",
            ),
            types.FunctionDeclaration(
                name="stop_hand_tracking",
                description="Turn off hand tracking mode and release the camera.",
            ),
        ]),
        # Native Google Search grounding
        types.Tool(google_search=types.GoogleSearch()),
    ]


# ──────────────────────────────────────────────
# Main Agent Class
# ──────────────────────────────────────────────

class GeminiLiveAgent:
    """
    Real-time voice agent using the Gemini Multimodal Live API.
    Streams microphone audio → Gemini → speaker audio, with full tool support.
    """

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is missing from .env")

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash-native-audio-latest"

        self.pa = pyaudio.PyAudio()
        self.mic_format = pyaudio.paInt16
        self.channels = 1
        self.mic_rate = 16000
        self.speaker_rate = 24000
        self.chunk = 512

        self._should_exit = asyncio.Event()
        # Thread-safe audio playback queue — allows instant flush on interruption
        self._audio_queue: queue.Queue = queue.Queue()
        self._audio_stop = threading.Event()

    async def _mic_task(self, session, stream_in, loop):
        """Streams mic audio to Gemini via send_realtime_input."""
        try:
            while not self._should_exit.is_set():
                data = await loop.run_in_executor(None, stream_in.read, self.chunk, False)
                await session.send_realtime_input(
                    audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={self.mic_rate}")
                )
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not self._should_exit.is_set():
                print(f"🎙️ Mic error: {e}")
                self._should_exit.set()  # FATAL: Break deadlock on microphone/connection failure

    def _audio_player_thread(self, stream_out):
        """
        Background thread: drains the audio queue and writes to the PA stream.
        Runs independently of asyncio so write() never blocks the event loop.
        """
        import time
        buffering = True  # Starts out needing buffer
        while not self._should_exit.is_set():
            # Apply Jitter buffering to prevent audio choppiness from poor network latency
            if buffering:
                if self._audio_queue.qsize() < 5 and not self._audio_stop.is_set():
                    time.sleep(0.02)
                    continue
                buffering = False
                
            try:
                chunk = self._audio_queue.get(timeout=0.05)
                if not self._audio_stop.is_set():
                    try:
                        stream_out.write(chunk)
                    except OSError:
                        # Stream was closed mid-write; exit gracefully
                        break
            except queue.Empty:
                # Queue ran dry because internet is slower than playback rate - start buffering again!
                buffering = True
                continue

    def _flush_audio_queue(self):
        """Instantly clears the audio queue to stop playback on interruption."""
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    async def _speaker_task(self, session, stream_out):
        """
        Receives audio from Gemini and queues it for playback.
        Audio is written to the speaker on a background thread so this
        coroutine is always free to process interruption signals immediately.
        """
        # Start the background audio playback thread
        self.player_thread = threading.Thread(
            target=self._audio_player_thread,
            args=(stream_out,),
            daemon=True,
            name="JarvisAudioPlayer"
        )
        self.player_thread.start()

        try:
            while not self._should_exit.is_set():
                async for response in session.receive():
                    # Reset the inactivity timer every time we get a response
                    self._last_interaction_time = time.time()
                    
                    # Queue audio for the background player thread
                    if response.data:
                        self._audio_queue.put(response.data)

                    # Gemini detected the user speaking — stop current audio instantly
                    if response.server_content and response.server_content.interrupted:
                        self._flush_audio_queue()

                    # Handle tool call
                    if response.tool_call:
                        await self._handle_tool_call(session, response.tool_call)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not self._should_exit.is_set():
                print(f"🔊 Speaker error: {e}")
                self._should_exit.set()  # FATAL: Break the deadlock on connection drop

    async def _inactivity_task(self, session):
        """Monitors the connection for silence. Closes if inactive for 40 seconds."""
        try:
            while not self._should_exit.is_set():
                await asyncio.sleep(1)
                # If it's been > 40s since the last activity, auto-exit
                if time.time() - self._last_interaction_time > 40.0:
                    print("\n💤 Jarvis has been silent for 40 seconds. Auto-sleeping...")
                    try:
                        # Prompt the model to naturally say goodbye and exit itself
                        await session.send(input="The user has been silent for 40 seconds. Please say exactly 'Goodbye' to let the user know you are leaving, and then immediately call the exit_session tool.", end_of_turn=True)
                    except Exception as e:
                        # Fallback if connection is already dead
                        self._should_exit.set()
                    break
        except asyncio.CancelledError:
            pass

    async def _handle_tool_call(self, session, tool_call):
        """Executes a Gemini tool call locally and sends the result back."""
        responses = []
        for fc in tool_call.function_calls:
            name = fc.name
            args = dict(fc.args) if fc.args else {}
            print(f"\n🔧 Jarvis calling tool: {name}({args})")

            try:
                handler = TOOL_HANDLERS.get(name)
                if handler:
                    result = await asyncio.to_thread(handler, args)
                else:
                    result = f"Unknown tool: {name}"
            except Exception as e:
                result = f"Tool error: {e}"

            # Special signal: exit_session requested
            if result == "__EXIT__":
                print("\n👋 Jarvis: Goodbye! Returning to text mode.")
                await session.send_tool_response(
                    function_responses=[types.FunctionResponse(
                        name=name, id=fc.id,
                        response={"output": "Session ended."}
                    )]
                )
                await asyncio.sleep(1.5)
                self._should_exit.set()
                return

            print(f"   ✅ Tool result: {str(result)[:100]}...")
            responses.append(types.FunctionResponse(
                name=name,
                id=fc.id,
                response={"output": str(result)}
            ))

        if responses:
            await session.send_tool_response(function_responses=responses)

    async def run(self):
        """Opens audio streams + WebSocket, runs mic and speaker tasks concurrently."""
        loop = asyncio.get_event_loop()
        self._should_exit.clear()

        # Map the microphone device
        mic_index_str = os.getenv('CIPHER_MIC_DEVICE')
        input_args = {
            "format": self.mic_format,
            "channels": self.channels,
            "rate": self.mic_rate,
            "input": True,
            "frames_per_buffer": self.chunk
        }
        if mic_index_str and mic_index_str.isdigit():
            input_args["input_device_index"] = int(mic_index_str)

        stream_in = self.pa.open(**input_args)
        stream_out = self.pa.open(
            format=self.mic_format, channels=self.channels,
            rate=self.speaker_rate, output=True
        )

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            tools=_build_tools(),
            system_instruction=types.Content(parts=[types.Part.from_text(text=(
                "You are Jarvis, Chetan's highly intelligent, fast, and helpful real-time voice assistant. "
                "Be concise and conversational — no markdown, no bullet points as responses will be spoken aloud. "
                "You can control Chetan's Windows PC with these tools: "
                "play_on_youtube (play music/videos), open_url (open websites), open_app (launch apps like Chrome, Spotify, VS Code), "
                "open_folder (open file explorer), set_volume / mute_volume (audio control), "
                "take_screenshot (capture screen), create_note / read_notes (personal notes), "
                "set_reminder (timed Windows notifications), system_control (sleep/shutdown/restart/lock PC). "
                "You also have: search_web for internet queries, read_file / list_files for local files, "
                "get_system_stats for PC performance, get_battery_status for battery info, read_memory for personal info about Chetan. "
                "You can also use 'start_hand_tracking' to enable the camera so the user can control their PC with their hands, and 'stop_hand_tracking' to turn it off. "
                "Use tools proactively. When the user says goodbye or stop, immediately call exit_session."
            ))])
        )

        print(f"\n🌐 Connecting Jarvis to {self.model}...")

        try:
            async with self.client.aio.live.connect(model=self.model, config=config) as session:
                print("✅ Jarvis is live! Speak naturally. Say 'Goodbye Jarvis' to exit.\n")
                
                # Tell Jarvis to audibly greet the user before passing the mic natively
                await session.send(input="The user just woke you up. Please greet them warmly, state you are ready, and then wait.", end_of_turn=True)

                mic_t = asyncio.create_task(self._mic_task(session, stream_in, loop))
                spk_t = asyncio.create_task(self._speaker_task(session, stream_out))
                
                self._last_interaction_time = time.time()
                inactivity_t = asyncio.create_task(self._inactivity_task(session))

                try:
                    await self._should_exit.wait()
                except asyncio.CancelledError:
                    pass
                finally:
                    inactivity_t.cancel()
                    mic_t.cancel()
                    spk_t.cancel()
                    await asyncio.gather(inactivity_t, mic_t, spk_t, return_exceptions=True)

        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n🛑 Jarvis stopped.")
        except Exception as e:
            print(f"\n❌ Gemini Live error: {e}")
            traceback.print_exc()
        finally:
            # Let the background read() ThreadPoolExecutor naturally return 
            # and break its OS loop BEFORE we pull the rug out with stop_stream()
            # This completely patches the PyAudio Deadlock!
            await asyncio.sleep(0.5)
            
            # Ensure the background audio player thread stops trying to write
            # before we violently close the stream it's using
            if hasattr(self, 'player_thread') and self.player_thread.is_alive():
                self._should_exit.set() # extra safety
                self.player_thread.join(timeout=0.5)
                
            # Do NOT call self.pa.terminate() here! 
            # PyAudio and sounddevice (used by the wake word detector) share the PortAudio C-DLL.
            try:
                if stream_in.is_active():
                    stream_in.stop_stream()
                stream_in.close()
            except Exception: pass
            
            try:
                if stream_out.is_active():
                    stream_out.stop_stream()
                stream_out.close()
            except Exception: pass
