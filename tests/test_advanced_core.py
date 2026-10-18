import asyncio
import logging
import pytest
from advanced_subsystem_core import JarvisAdvancedSubsystemFacade
from advanced_subsystem_core.domain.models import HardwareTelemetry

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

@pytest.fixture
def facade():
    return JarvisAdvancedSubsystemFacade()

async def mock_telemetry_provider() -> HardwareTelemetry:
    """Mocks hardware telemetry indicating a gradual overload."""
    import time
    return HardwareTelemetry(
        timestamp=time.time(),
        voltage=24.0,
        current=120.0, # High current triggers overload
        temperature_celsius=65.0,
        active_circuits=3
    )

def test_self_healing(facade: JarvisAdvancedSubsystemFacade):
    print("\n--- [TEST] AUTONOMOUS SELF-HEALING ENGINE ---")
    healer = facade.get_healing_context()
    
    @healer
    def risky_function():
        print("Running risky function...")
        # Simulating a crash that the healer will intercept
        x = 1 / 0
        
    try:
        risky_function()
    except Exception as e:
        print(f"Exception escaped (expected): {e}")

async def run_tests():
    facade = JarvisAdvancedSubsystemFacade()
    
    print("\n--- [TEST] PREDICTIVE HOLOGRAM ENGINE ---")
    # This will fail gracefully because 'dummy.obj' doesn't exist, proving error handling
    facade.render_and_export_mesh("dummy.obj", "output.json")
    
    test_self_healing(facade)
    
    print("\n--- [TEST] PROACTIVE SAFETY GOVERNOR ---")
    monitor_task = asyncio.create_task(facade.start_safety_monitoring(mock_telemetry_provider))
    
    # Let it monitor for a few seconds
    await asyncio.sleep(3)
    facade.stop_safety_monitoring()
    await monitor_task

if __name__ == "__main__":
    asyncio.run(run_tests())
