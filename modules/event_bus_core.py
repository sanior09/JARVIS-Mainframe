import asyncio
import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Union

logger = logging.getLogger("EventBus")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(ch)

class EventPriority(enum.IntEnum):
    """Lower integer value = Higher Priority"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

class EventChannel(enum.Enum):
    AUDIO = "audio"
    HUD = "hud"
    HARDWARE_SAFETY = "hardware_safety"
    AI_THOUGHT = "ai_thought"
    SYSTEM = "system"
    WILDCARD = "*"

@dataclass
class SystemEvent:
    channel: EventChannel
    topic: str
    priority: EventPriority = EventPriority.NORMAL
    payload: Dict[str, Any] = field(default_factory=dict)
    sender_id: str = "core"
    
    event_id: str = field(init=False)
    timestamp: float = field(init=False)

    def __post_init__(self):
        self.event_id = str(uuid.uuid4())
        self.timestamp = time.time()

    def __lt__(self, other: 'SystemEvent') -> bool:
        """
        Priority Queue sorting logic:
        1. Compare Priority Level (Lower Int = Higher Priority)
        2. If Priority is equal, compare Timestamp (Older = Process First)
        """
        if self.priority == other.priority:
            return self.timestamp < other.timestamp
        return self.priority < other.priority

CallbackType = Union[Callable[[SystemEvent], None], Callable[[SystemEvent], Coroutine[Any, Any, None]]]

class SubscriptionRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: Dict[EventChannel, Set[CallbackType]] = {channel: set() for channel in EventChannel}
        self._topic_subscribers: Dict[str, Set[CallbackType]] = {}

    def subscribe(self, channel: EventChannel, callback: CallbackType, topic_pattern: Optional[str] = None):
        with self._lock:
            if topic_pattern:
                if topic_pattern not in self._topic_subscribers:
                    self._topic_subscribers[topic_pattern] = set()
                self._topic_subscribers[topic_pattern].add(callback)
            else:
                self._subscribers[channel].add(callback)

    def unsubscribe(self, channel: EventChannel, callback: CallbackType, topic_pattern: Optional[str] = None):
        with self._lock:
            try:
                if topic_pattern:
                    self._topic_subscribers[topic_pattern].remove(callback)
                else:
                    self._subscribers[channel].remove(callback)
            except KeyError:
                pass

    def get_callbacks(self, event: SystemEvent) -> List[CallbackType]:
        with self._lock:
            callbacks: Set[CallbackType] = set()
            
            callbacks.update(self._subscribers[event.channel])
            
            callbacks.update(self._subscribers[EventChannel.WILDCARD])
            
            if event.topic in self._topic_subscribers:
                callbacks.update(self._topic_subscribers[event.topic])
            
            return list(callbacks)

class UnifiedEventBus:
    _instance = None
    _creation_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Thread-safe Singleton implementation."""
        with cls._creation_lock:
            if cls._instance is None:
                cls._instance = super(UnifiedEventBus, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self):
        self.registry = SubscriptionRegistry()
        self.queue: Optional[asyncio.PriorityQueue] = None
        self._is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def subscribe(self, channel: EventChannel, callback: CallbackType, topic_pattern: Optional[str] = None):
        self.registry.subscribe(channel, callback, topic_pattern)

    async def publish(self, event: SystemEvent):
        """Standard Async Publish. Throws event into PriorityQueue."""
        if not self._is_running or self.queue is None:
            logger.warning(f"EventBus is not running. Dropping event: {event.topic}")
            return
            
        await self.queue.put(event)
        logger.debug(f"Pushed Event: [{event.priority.name}] {event.topic}")

    def publish_threadsafe(self, event: SystemEvent):
        """
        Thread-safe Publisher. 
        Use this when publishing from synchronous hardware/UI threads (e.g. OpenCV, PyAudio).
        """
        if not self._is_running or self._loop is None:
            return

        def _sync_put():
            self.queue.put_nowait(event)
            logger.debug(f"(ThreadSafe) Pushed Event: [{event.priority.name}] {event.topic}")

        self._loop.call_soon_threadsafe(_sync_put)

    async def start_dispatch_loop(self):
        """Background worker that continuously routes events concurrently."""
        self._loop = asyncio.get_running_loop()
        self.queue = asyncio.PriorityQueue()
        self._is_running = True
        logger.info("Unified Event Bus Dispatch Loop Started.")

        while self._is_running:
            try:
                
                event: SystemEvent = await self.queue.get()
                
                callbacks = self.registry.get_callbacks(event)
                
                for callback in callbacks:
                    
                    asyncio.create_task(self._safe_execute(callback, event))
                    
                self.queue.task_done()
            except asyncio.CancelledError:
                self._is_running = False
                break
            except Exception as e:
                logger.error(f"EventBus Dispatcher Error: {e}")

    async def _safe_execute(self, callback: CallbackType, event: SystemEvent):
        """Isolates exception failures so a bad callback doesn't crash the Bus.
        
        - Async callbacks are awaited directly.
        - Sync callbacks are offloaded to a thread pool via run_in_executor()
          to prevent blocking the asyncio event loop on heavy operations.
        """
        cb_name = getattr(callback, '__name__', str(callback))
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, callback, event)
        except Exception as e:
            logger.error(f"Error executing callback '{cb_name}' for event '{event.topic}': {e}")

    def stop(self):
        self._is_running = False

async def demo_app():
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    print("\n" + "="*70)
    print(" 🚦 STARTING UNIFIED EVENT BUS DEMO")
    print("="*70)

    bus = UnifiedEventBus()
    
    async def hud_listener(event: SystemEvent):
        
        await asyncio.sleep(0.1)
        print(f"   [HUD RENDER] Processed UI Update: {event.topic} (Payload: {event.payload})")
        
    def hardware_safety_listener(event: SystemEvent):
        
        print(f"\n🚨 [CRITICAL ALERT] EMERGENCY PROTOCOL TRIGGERED: {event.topic}!")
        print(f"   -> Payload: {event.payload}\n")

    bus.subscribe(EventChannel.HUD, hud_listener)
    bus.subscribe(EventChannel.HARDWARE_SAFETY, hardware_safety_listener)

    dispatch_task = asyncio.create_task(bus.start_dispatch_loop())

    await asyncio.sleep(0.1)

    def heavy_ui_thread():
        for i in range(5):
            ev = SystemEvent(
                channel=EventChannel.HUD,
                topic=f"RenderFrame_{i}",
                priority=EventPriority.NORMAL,
                payload={"frame_id": i}
            )
            bus.publish_threadsafe(ev)
            time.sleep(0.01) 
            
    thread = threading.Thread(target=heavy_ui_thread)
    thread.start()

    await asyncio.sleep(0.02) 
    
    critical_event = SystemEvent(
        channel=EventChannel.HARDWARE_SAFETY,
        topic="VOLTAGE_SPIKE_DETECTED",
        priority=EventPriority.CRITICAL,
        payload={"voltage": "240V", "limit": "220V", "action": "CUT_POWER"}
    )
    
    print("\n>> Injecting CRITICAL Event into the queued UI updates...\n")
    await bus.publish(critical_event)

    await asyncio.sleep(1.0)
    
    bus.stop()
    dispatch_task.cancel()
    
    print("\n✅ Unified Event Bus Test Completed Successfully!\n" + "="*70)

if __name__ == "__main__":
    asyncio.run(demo_app())
