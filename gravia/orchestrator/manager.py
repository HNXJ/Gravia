import asyncio
import json
import os
import httpx
try:
    import aiofiles
except ImportError:
    # Fallback for environment without aiofiles
    aiofiles = None

class OrchestratorManager:
    def __init__(self, state_path: str = "local/sov_context_window.json", 
                 history_path: str = "local/sov_messages.json",
                 m3_host: str = "http://127.0.0.1:1234"):
        self.state_path = state_path
        self.history_path = history_path
        self.m3_host = m3_host
        self.api_base = f"{self.m3_host}/v1"
        self.vram_lock = asyncio.Lock()
        self.active_model = None
        
        # Ensure files exist
        for p in [self.state_path, self.history_path]:
            d = os.path.dirname(p)
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            
        if not os.path.exists(self.history_path):
            with open(self.history_path, 'w') as f:
                json.dump([{"role": "system", "content": "Sovereign State Initialized. GAMMA Protocol Active."}], f)
        
        if not os.path.exists(self.state_path):
            with open(self.state_path, 'w') as f:
                json.dump({"current_specialist": None, "council_state": "IDLE"}, f)

    async def _read_history(self):
        """Reads message history from sov_messages.json."""
        if aiofiles:
            async with aiofiles.open(self.history_path, mode='r') as f:
                contents = await f.read()
                return json.loads(contents)
        else:
            return await asyncio.to_thread(self._read_history_sync)

    def _read_history_sync(self):
        with open(self.history_path, 'r') as f:
            return json.load(f)

    async def _write_history(self, history_data):
        """Writes message history to sov_messages.json."""
        if aiofiles:
            async with aiofiles.open(self.history_path, mode='w') as f:
                await f.write(json.dumps(history_data, indent=2))
        else:
            await asyncio.to_thread(self._write_history_sync, history_data)

    def _write_history_sync(self, history_data):
        with open(self.history_path, 'w') as f:
            json.dump(history_data, f, indent=2)

    async def _read_meta_state(self):
        """Reads meta-state from sov_context_window.json."""
        if aiofiles:
            async with aiofiles.open(self.state_path, mode='r') as f:
                contents = await f.read()
                return json.loads(contents)
        else:
            return await asyncio.to_thread(self._read_meta_state_sync)

    def _read_meta_state_sync(self):
        with open(self.state_path, 'r') as f:
            return json.load(f)

    async def _write_meta_state(self, meta_data):
        """Writes meta-state to sov_context_window.json."""
        if aiofiles:
            async with aiofiles.open(self.state_path, mode='w') as f:
                await f.write(json.dumps(meta_data, indent=2))
        else:
            await asyncio.to_thread(self._write_meta_state_sync, meta_data)

    def _write_meta_state_sync(self, meta_data):
        with open(self.state_path, 'w') as f:
            json.dump(meta_data, f, indent=2)

    async def delegate(self, task_payload: str, target_model: str) -> str:
        """
        The core gateway. Enforces VRAM lock, handles loading, and executes the prompt.
        """
        async with self.vram_lock:
            if self.active_model != target_model:
                await self._enforce_unload_all()
                await self._load_model(target_model)
            
            return await self._execute_and_record(task_payload, target_model)

    async def _enforce_unload_all(self):
        print("[VRAM GUARD] Flushing Unified Memory...")
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"{self.m3_host}/v1/models/unload", json={"model": self.active_model})
            except Exception as e:
                print(f"[WARNING] Unload signal dropped or unsupported: {e}")
        self.active_model = None
        await asyncio.sleep(2) # Physical VRAM flush buffer

    async def _load_model(self, target_model: str):
        print(f"[VRAM GUARD] Allocating memory for {target_model}...")
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                await client.post(f"{self.m3_host}/v1/models/load", json={"model": target_model})
            except Exception as e:
                print(f"[WARNING] Pre-load signal dropped or unsupported: {e}")
        self.active_model = target_model
        await asyncio.sleep(2) # Physical VRAM load buffer

    async def _execute_and_record(self, task_payload: str, target_model: str) -> str:
        # Load message history
        messages = await self._read_history()
        
        # Multimodal Protection: Strip/Compress before text-only handoff
        messages = self._strip_vision_tokens(messages)
        messages = self._compress_context(messages)
        
        # Append user task
        messages.append({"role": "user", "content": task_payload})
        
        print(f"[ORCHESTRATOR] Routing execution to {target_model}...")
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                json={
                    "model": target_model,
                    "messages": messages,
                    "temperature": 0.2
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                assistant_reply = result['choices'][0]['message']['content']
                
                # Append response and save history
                messages.append({"role": "assistant", "content": assistant_reply})
                await self._write_history(messages)
                
                # Update meta-state
                meta = await self._read_meta_state()
                meta["current_specialist"] = target_model
                await self._write_meta_state(meta)
                
                return assistant_reply
            else:
                error_msg = f"[ERROR] Inference-Node API returned {response.status_code}: {response.text}"
                print(error_msg)
                return error_msg

    def _strip_vision_tokens(self, messages: list) -> list:
        """Removes base64 images and complex multimodal objects to protect text models."""
        sanitized = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                text_only = [item["text"] for item in content if item.get("type") == "text"]
                sanitized.append({"role": msg["role"], "content": " ".join(text_only)})
            elif isinstance(content, str) and "data:image" in content:
                sanitized.append({"role": msg["role"], "content": "[Vision Token Stripped by Sovereign Orchestrator]"})
            else:
                sanitized.append(msg)
        return sanitized

    def _compress_context(self, messages: list, max_messages: int = 10) -> list:
        """Enforces a sliding window to prevent Inference-Node context overflows.
        Ensures the sequence after the system prompt starts with a 'user' message.
        """
        if len(messages) <= max_messages:
            return messages
            
        # Keep the system prompt
        system_msg = messages[0] if messages and messages[0].get("role") == "system" else None
        
        # Take the last N messages
        start_idx = len(messages) - (max_messages - 1)
        # Ensure we start with a user message to satisfy model templates
        while start_idx < len(messages) and messages[start_idx].get("role") != "user":
            start_idx += 1
            
        new_messages = messages[start_idx:]
        if system_msg:
            return [system_msg] + new_messages
        return new_messages

# Global Singleton Instance for Gravia
sov_orchestrator = OrchestratorManager()
