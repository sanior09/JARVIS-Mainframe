import asyncio
import binascii
import enum
import logging
import multiprocessing
import multiprocessing.shared_memory
import struct
import time
from dataclasses import dataclass
from typing import Any, Optional, Tuple

logger = logging.getLogger("NeuralIPC")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(ch)

class IPCPriority(enum.IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class IPCMessageType(enum.IntEnum):
    UNKNOWN = 0
    HUD_UPDATE = 1
    PCM_AUDIO = 2
    VIDEO_FRAME = 3
    TELEMETRY = 4
    INTERRUPT = 5

@dataclass
class IPCMessageHeader:
    """
    Fixed Size Header (32 bytes):
    Magic (4s) | Type (H) | Priority (H) | Length (I) | Seq (Q) | Timestamp (d) | CRC32 (I)
    """
    magic: bytes = b'NRAL'
    msg_type: IPCMessageType = IPCMessageType.UNKNOWN
    priority: IPCPriority = IPCPriority.NORMAL
    payload_length: int = 0
    sequence_id: int = 0
    timestamp: float = 0.0
    crc32: int = 0

    FORMAT = "<4s H H I Q d I"
    SIZE = struct.calcsize(FORMAT)  

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.magic,
            self.msg_type.value,
            self.priority.value,
            self.payload_length,
            self.sequence_id,
            self.timestamp,
            self.crc32
        )

    @classmethod
    def unpack(cls, data: bytes) -> 'IPCMessageHeader':
        unpacked = struct.unpack(cls.FORMAT, data)
        return cls(
            magic=unpacked[0],
            msg_type=IPCMessageType(unpacked[1]),
            priority=IPCPriority(unpacked[2]),
            payload_length=unpacked[3],
            sequence_id=unpacked[4],
            timestamp=unpacked[5],
            crc32=unpacked[6]
        )

class SharedRingBuffer:
    """
    Ring Buffer over Python multiprocessing.shared_memory.
    Control Block (8 bytes): [Head (4 bytes) | Tail (4 bytes)]
    Data Block: The rest of the memory.
    """
    CTRL_FMT = "<I I"
    CTRL_SIZE = struct.calcsize(CTRL_FMT)

    def __init__(self, name: str, size: int, create: bool = False):
        self.name = name
        self.size = size
        self.create = create
        self.shm: Optional[multiprocessing.shared_memory.SharedMemory] = None
        self.capacity = size - self.CTRL_SIZE

    def _spinlock_acquire(self):
        
        pass 

    def open(self):
        try:
            if self.create:
                self.shm = multiprocessing.shared_memory.SharedMemory(name=self.name, create=True, size=self.size)
                
                self._write_ctrl(0, 0)
                logger.info(f"SharedMemory '{self.name}' created (size={self.size} bytes).")
            else:
                self.shm = multiprocessing.shared_memory.SharedMemory(name=self.name, create=False)
                logger.info(f"SharedMemory '{self.name}' attached.")
        except FileExistsError:
            logger.warning(f"SharedMemory '{self.name}' already exists. Attaching instead.")
            self.shm = multiprocessing.shared_memory.SharedMemory(name=self.name, create=False)
        except FileNotFoundError:
            logger.error(f"SharedMemory '{self.name}' not found. Cannot attach.")
            raise

    def close(self, unlink: bool = False):
        if self.shm is not None:
            self.shm.close()
            if unlink:
                try:
                    self.shm.unlink()
                    logger.info(f"SharedMemory '{self.name}' unlinked/freed.")
                except FileNotFoundError:
                    pass
            self.shm = None

    def _read_ctrl(self) -> Tuple[int, int]:
        """Reads (head, tail) from control block."""
        return struct.unpack_from(self.CTRL_FMT, self.shm.buf, 0)

    def _write_ctrl(self, head: int, tail: int):
        """Writes (head, tail) to control block."""
        struct.pack_into(self.CTRL_FMT, self.shm.buf, 0, head, tail)

    def get_free_space(self) -> int:
        head, tail = self._read_ctrl()
        if head >= tail:
            return self.capacity - (head - tail) - 1
        else:
            return (tail - head) - 1

    def write(self, data: bytes) -> bool:
        """Zero-copy write into ring buffer. Returns False if full."""
        length = len(data)
        head, tail = self._read_ctrl()
        
        free_space = self.capacity - (head - tail) - 1 if head >= tail else (tail - head) - 1
        if length > free_space:
            return False  

        start_idx = self.CTRL_SIZE + head
        end_idx = start_idx + length

        if end_idx <= self.size:
            
            self.shm.buf[start_idx:end_idx] = data
        else:
            
            part1_len = self.size - start_idx
            part2_len = length - part1_len
            self.shm.buf[start_idx:] = data[:part1_len]
            self.shm.buf[self.CTRL_SIZE : self.CTRL_SIZE + part2_len] = data[part1_len:]

        new_head = (head + length) % self.capacity
        self._write_ctrl(new_head, tail)
        return True

    def read(self, length: int) -> Optional[bytes]:
        """Zero-copy read from ring buffer. Returns None if not enough data."""
        head, tail = self._read_ctrl()
        
        used_space = (head - tail) if head >= tail else self.capacity - (tail - head)
        if used_space < length:
            return None  

        start_idx = self.CTRL_SIZE + tail
        end_idx = start_idx + length

        if end_idx <= self.size:
            data = bytes(self.shm.buf[start_idx:end_idx])
        else:
            part1_len = self.size - start_idx
            part2_len = length - part1_len
            data = bytes(self.shm.buf[start_idx:]) + bytes(self.shm.buf[self.CTRL_SIZE : self.CTRL_SIZE + part2_len])

        new_tail = (tail + length) % self.capacity
        self._write_ctrl(head, new_tail)
        return data

class NeuralIPCChannel:
    """
    High-level IPC interface managing framing, CRC checks, and synchronization.
    Fully supports Async Context Managers.
    """
    def __init__(self, name: str, size: int, lock: Any, is_server: bool = False):
        self.name = name
        self.size = size
        self.lock = lock
        self.is_server = is_server
        self.buffer = SharedRingBuffer(name, size, create=is_server)
        self._seq_id = 0

    async def __aenter__(self):
        self.buffer.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.buffer.close(unlink=self.is_server)

    async def send(self, msg_type: IPCMessageType, payload: bytes, priority: IPCPriority = IPCPriority.NORMAL):
        """Asynchronously sends a framed message via Shared Memory."""
        self._seq_id += 1
        crc = binascii.crc32(payload) & 0xFFFFFFFF
        
        header = IPCMessageHeader(
            msg_type=msg_type,
            priority=priority,
            payload_length=len(payload),
            sequence_id=self._seq_id,
            timestamp=time.time(),
            crc32=crc
        )
        
        packet = header.pack() + payload

        while True:
            with self.lock:
                success = self.buffer.write(packet)
            
            if success:
                break
            
            await asyncio.sleep(0.001)

    async def receive(self) -> Optional[Tuple[IPCMessageHeader, bytes]]:
        """Asynchronously receives and unpacks a framed message."""
        while True:
            with self.lock:
                
                header_data = self.buffer.read(IPCMessageHeader.SIZE)
                
                if header_data:
                    header = IPCMessageHeader.unpack(header_data)
                    payload_data = self.buffer.read(header.payload_length)
                    
                    if payload_data:
                        
                        calc_crc = binascii.crc32(payload_data) & 0xFFFFFFFF
                        if calc_crc != header.crc32:
                            logger.error(f"CRC Mismatch! Expected {header.crc32}, got {calc_crc}. Dropping packet.")
                            return None
                            
                        return header, payload_data
                    else:
                        
                        logger.error("Corrupted Ring Buffer State: Header read but no payload.")
                        return None
            
            await asyncio.sleep(0.001)

def _producer_process(ipc_name: str, lock: Any):
    """Simulates JARVIS Core sending data to PyQt6 HUD."""
    async def run():
        logger.info("Producer Process Started.")
        async with NeuralIPCChannel(ipc_name, 1024 * 1024, lock, is_server=True) as channel:
            for i in range(5):
                msg = f"HUD_UPDATE_FRAME_{i}".encode('utf-8')
                await channel.send(IPCMessageType.HUD_UPDATE, msg, IPCPriority.HIGH)
                logger.info(f"[PRODUCER] Sent: {msg}")
                await asyncio.sleep(0.1)
                
            await channel.send(IPCMessageType.INTERRUPT, b"SHUTDOWN")
            logger.info("[PRODUCER] Sent SHUTDOWN sequence.")
            await asyncio.sleep(0.5) 
            
    asyncio.run(run())

def _consumer_process(ipc_name: str, lock: Any):
    """Simulates PyQt6 HUD reading data from JARVIS Core."""
    async def run():
        logger.info("Consumer Process Started.")
        
        await asyncio.sleep(0.1) 
        
        async with NeuralIPCChannel(ipc_name, 1024 * 1024, lock, is_server=False) as channel:
            while True:
                result = await channel.receive()
                if result:
                    header, payload = result
                    logger.info(f"[CONSUMER] Received Type: {header.msg_type.name}, Seq: {header.sequence_id}, Payload: {payload}")
                    if header.msg_type == IPCMessageType.INTERRUPT:
                        logger.info("[CONSUMER] Interrupt received. Shutting down.")
                        break
                        
    asyncio.run(run())

if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
            
    print("\n" + "="*50)
    print(" 🧠 STARTING NEURAL IPC SHARED MEMORY SIMULATION")
    print("="*50)
    
    multiprocessing.set_start_method('spawn', force=True)
    
    SHARED_MEM_NAME = "jarvis_neural_ipc_bus"
    ipc_lock = multiprocessing.Lock()
    
    p1 = multiprocessing.Process(target=_producer_process, args=(SHARED_MEM_NAME, ipc_lock))
    p2 = multiprocessing.Process(target=_consumer_process, args=(SHARED_MEM_NAME, ipc_lock))
    
    p2.start()
    p1.start()
    
    p1.join()
    p2.join()
    
    print("\n✅ Multi-Process Simulation Completed Successfully!\n" + "="*50)
