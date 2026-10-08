"""
deriv_client.py
Handles WebSocket connection to Deriv API for tick data.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional, List, Dict, Any

import websockets

# Deriv WebSocket endpoint
DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"

# Synthetic index symbols available on Deriv
SYMBOLS = {
    "Volatility 10 Index": "R_10",
    "Volatility 25 Index": "R_25",
    "Volatility 50 Index": "R_50",
    "Volatility 75 Index": "R_75",
    "Volatility 100 Index": "R_100",
    "Volatility 10 (1s) Index": "1HZ10V",
    "Volatility 25 (1s) Index": "1HZ25V",
    "Volatility 50 (1s) Index": "1HZ50V",
    "Volatility 75 (1s) Index": "1HZ75V",
    "Volatility 100 (1s) Index": "1HZ100V",
}

logger = logging.getLogger(__name__)


class DerivClient:
    """Async WebSocket client for Deriv API tick data."""

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._req_id = 0
        self._connected = False

    def _next_req_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def connect(self):
        """Establish WebSocket connection and optionally authorize."""
        self.ws = await websockets.connect(DERIV_WS_URL)
        self._connected = True
        logger.info("Connected to Deriv WebSocket API")

        if self.api_token:
            await self._authorize()

    async def _authorize(self):
        """Send authorization request if token is provided."""
        req_id = self._next_req_id()
        await self.ws.send(json.dumps({
            "authorize": self.api_token,
            "req_id": req_id
        }))
        response = await self._recv_response(req_id)
        if "error" in response:
            logger.error(f"Authorization failed: {response['error']['message']}")
            raise ConnectionError(f"Auth failed: {response['error']['message']}")
        logger.info("Authorization successful")

    async def _recv_response(self, req_id: int, timeout: float = 10.0) -> Dict:
        """Receive a specific response by req_id."""
        start = asyncio.get_event_loop().time()
        while True:
            remaining = timeout - (asyncio.get_event_loop().time() - start)
            if remaining <= 0:
                raise TimeoutError(f"Timeout waiting for req_id {req_id}")
            raw = await asyncio.wait_for(self.ws.recv(), timeout=remaining)
            data = json.loads(raw)
            if data.get("req_id") == req_id:
                return data

    async def get_ticks_history(
        self, symbol: str, count: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical ticks for a symbol.

        Returns a list of dicts: [{"epoch": ..., "quote": ...}, ...]
        """
        req_id = self._next_req_id()
        request = {
            "ticks_history": symbol,
            "count": count,
            "end": "latest",
            "style": "ticks",
            "req_id": req_id,
        }
        await self.ws.send(json.dumps(request))
        response = await self._recv_response(req_id)

        if "error" in response:
            raise RuntimeError(f"API error: {response['error']['message']}")

        history = response.get("history", {})
        prices = history.get("prices", [])
        times = history.get("times", [])

        ticks = [
            {"epoch": t, "quote": float(p)}
            for t, p in zip(times, prices)
        ]
        logger.info(f"Fetched {len(ticks)} historical ticks for {symbol}")
        return ticks

    async def stream_ticks(self, symbol: str) -> AsyncGenerator[Dict, None]:
        """
        Subscribe to live tick stream.

        Yields each tick as {"epoch": ..., "quote": ...}.
        """
        req_id = self._next_req_id()
        await self.ws.send(json.dumps({
            "ticks": symbol,
            "subscribe": 1,
            "req_id": req_id,
        }))

        # Wait for subscription confirmation
        while True:
            raw = await self.ws.recv()
            data = json.loads(raw)

            if data.get("msg_type") == "tick" and "tick" in data:
                tick = data["tick"]
                yield {
                    "epoch": tick.get("epoch"),
                    "quote": float(tick.get("quote", 0)),
                }
            elif data.get("msg_type") == "error":
                logger.error(f"Stream error: {data}")
                break

    async def close(self):
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self._connected = False
            logger.info("WebSocket connection closed")
