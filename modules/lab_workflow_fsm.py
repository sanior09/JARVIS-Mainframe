"""
lab_workflow_fsm.py
Module 1: Engineering State Machine Manager

Responsible for managing the lifecycle of engineering tasks (Design -> Safety Check -> Sandbox -> Assembly -> Test)
using a Finite State Machine (FSM) pattern with rigorous guard conditions.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, List, Optional, Type

# Setup Module Logger
logger = logging.getLogger("LabWorkflowFSM")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class FSMException(Exception):
    """Base exception for State Machine errors."""
    pass


class TransitionError(FSMException):
    """Raised when an invalid state transition is attempted."""
    pass


class GuardConditionFailedError(FSMException):
    """Raised when a guard condition prevents a state transition."""
    pass


class WorkflowState(Enum):
    IDLE = auto()
    DESIGN = auto()
    SAFETY_CHECK = auto()
    SANDBOX = auto()
    ASSEMBLY = auto()
    TEST = auto()
    COMPLETED = auto()
    FAILED = auto()


class GuardCondition(ABC):
    """Abstract Base Class for defining transition guard conditions."""
    @abstractmethod
    async def check(self, context: Dict[str, any]) -> bool:
        """Returns True if the condition is met, False otherwise."""
        pass


class SafetyCheckGuard(GuardCondition):
    """Ensures basic safety validations are passed before proceeding."""
    async def check(self, context: Dict[str, any]) -> bool:
        logger.info("Evaluating SafetyCheckGuard...")
        await asyncio.sleep(0.1)  # Simulate checks
        return context.get("safety_passed", False)


class SandboxSuccessGuard(GuardCondition):
    """Ensures sandbox execution was successful."""
    async def check(self, context: Dict[str, any]) -> bool:
        logger.info("Evaluating SandboxSuccessGuard...")
        await asyncio.sleep(0.1)
        return context.get("sandbox_result") == "SUCCESS"


class StateTransition:
    """Defines a valid transition from one state to another with optional guards."""
    def __init__(self, from_state: WorkflowState, to_state: WorkflowState, guards: List[GuardCondition] = None):
        self.from_state = from_state
        self.to_state = to_state
        self.guards = guards or []


class LabWorkflowFSM:
    """Finite State Machine for managing laboratory workflow operations."""
    
    def __init__(self):
        self._current_state: WorkflowState = WorkflowState.IDLE
        self._context: Dict[str, any] = {}
        self._transitions: List[StateTransition] = self._build_transitions()

    def _build_transitions(self) -> List[StateTransition]:
        """Defines the allowed workflow state graph."""
        return [
            StateTransition(WorkflowState.IDLE, WorkflowState.DESIGN),
            StateTransition(WorkflowState.DESIGN, WorkflowState.SAFETY_CHECK),
            StateTransition(WorkflowState.SAFETY_CHECK, WorkflowState.SANDBOX, [SafetyCheckGuard()]),
            StateTransition(WorkflowState.SAFETY_CHECK, WorkflowState.FAILED),
            StateTransition(WorkflowState.SANDBOX, WorkflowState.ASSEMBLY, [SandboxSuccessGuard()]),
            StateTransition(WorkflowState.SANDBOX, WorkflowState.FAILED),
            StateTransition(WorkflowState.ASSEMBLY, WorkflowState.TEST),
            StateTransition(WorkflowState.TEST, WorkflowState.COMPLETED),
            StateTransition(WorkflowState.TEST, WorkflowState.FAILED),
        ]

    @property
    def current_state(self) -> WorkflowState:
        return self._current_state

    def update_context(self, key: str, value: any):
        """Updates the shared context used by guard conditions."""
        self._context[key] = value
        logger.debug(f"Context updated: {key} = {value}")

    async def advance_to(self, target_state: WorkflowState):
        """Attempts to transition to the target state asynchronously."""
        logger.info(f"Attempting transition: {self._current_state.name} -> {target_state.name}")
        
        # Find valid transition
        valid_transition = None
        for t in self._transitions:
            if t.from_state == self._current_state and t.to_state == target_state:
                valid_transition = t
                break
                
        if not valid_transition:
            raise TransitionError(f"Invalid transition from {self._current_state.name} to {target_state.name}")

        # Check guard conditions
        for guard in valid_transition.guards:
            if not await guard.check(self._context):
                raise GuardConditionFailedError(f"Guard {guard.__class__.__name__} failed for transition to {target_state.name}.")

        # Apply transition
        self._current_state = target_state
        logger.info(f"Transition successful. Current State: {self._current_state.name}")


if __name__ == "__main__":
    async def test_fsm():
        logger.info("--- Testing LabWorkflowFSM ---")
        fsm = LabWorkflowFSM()
        
        try:
            await fsm.advance_to(WorkflowState.DESIGN)
            await fsm.advance_to(WorkflowState.SAFETY_CHECK)
            
            # This should fail because safety context is not set
            try:
                logger.info("Attempting unauthorized Sandbox entry...")
                await fsm.advance_to(WorkflowState.SANDBOX)
            except GuardConditionFailedError as e:
                logger.warning(f"Caught expected guard failure: {e}")
                
            # Now set the context and try again
            logger.info("Setting safety_passed context...")
            fsm.update_context("safety_passed", True)
            await fsm.advance_to(WorkflowState.SANDBOX)
            
            # Set sandbox context to pass next stage
            fsm.update_context("sandbox_result", "SUCCESS")
            await fsm.advance_to(WorkflowState.ASSEMBLY)
            await fsm.advance_to(WorkflowState.TEST)
            await fsm.advance_to(WorkflowState.COMPLETED)
            
            logger.info("Workflow completed successfully.")
            
        except FSMException as e:
            logger.error(f"FSM Error: {e}")

    asyncio.run(test_fsm())
