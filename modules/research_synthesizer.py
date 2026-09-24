"""
research_synthesizer.py
Module 3: Autonomous Research & Graph Synthesizer

Responsible for processing extensive technical documents (e.g., datasheets)
into structured formats, and synthesizing system architectures into visual graphs.
"""

import ast
import json
import logging
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Setup Module Logger
logger = logging.getLogger("ResearchSynthesizer")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class SynthesizerException(Exception):
    """Base exception for the Research Synthesizer module."""
    pass


# Structured Output Model (Pydantic)
class DatasheetSpec(BaseModel):
    part_number: str = Field(default="UNKNOWN", description="The component part number")
    voltage_rating: Optional[str] = Field(default=None, description="Operating voltage range")
    power_consumption: Optional[str] = Field(default=None, description="Power usage (mW, W, etc.)")
    features: List[str] = Field(default_factory=list, description="Key features extracted")


class DatasheetAutoSummarizer:
    """
    Extracts key electrical/mechanical specifications from raw datasheet text.
    In production, this would interface with an LLM (e.g., Gemini/GPT-4) for semantic extraction.
    For this module, we use regex heuristics to simulate the extraction process.
    """
    
    def __init__(self):
        self.voltage_regex = re.compile(r"(\d+(?:\.\d+)?\s*V(?:DC|AC)?)", re.IGNORECASE)
        self.power_regex = re.compile(r"(\d+(?:\.\d+)?\s*(?:m|u|k)?W)", re.IGNORECASE)

    async def summarize_text(self, text: str, part_number: str) -> DatasheetSpec:
        """
        Parses text to extract structured datasheet specifications.
        """
        logger.info(f"Synthesizing datasheet for: {part_number}")
        import asyncio
        await asyncio.sleep(0.1) # Simulate I/O or LLM latency
        
        voltage_matches = self.voltage_regex.findall(text)
        power_matches = self.power_regex.findall(text)
        
        spec = DatasheetSpec(
            part_number=part_number,
            voltage_rating=voltage_matches[0] if voltage_matches else None,
            power_consumption=power_matches[0] if power_matches else None,
            features=[line.strip() for line in text.split('\\n') if "feature" in line.lower() or "support" in line.lower()]
        )
        return spec


class ArchitectureGraphVisualizer:
    """
    Analyzes Python source code using AST and generates a Mermaid.js diagram
    representing the class structures and their relationships.
    """
    
    def __init__(self):
        self.classes: List[str] = []
        self.relationships: List[tuple] = []
        
    def _extract_classes_and_bases(self, code: str):
        """Internal method to traverse AST and build relationship graph."""
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                self.classes.append(class_name)
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        self.relationships.append((base.id, class_name))
                        
    def generate_mermaid_diagram(self, source_code: str) -> str:
        """
        Generates a Mermaid.js class diagram from Python source code.
        """
        logger.info("Generating Mermaid.js Architecture Diagram...")
        self.classes.clear()
        self.relationships.clear()
        
        try:
            self._extract_classes_and_bases(source_code)
        except SyntaxError as e:
            logger.error(f"Failed to parse source code for graph generation: {e}")
            raise SynthesizerException(f"Syntax error in source code: {e}")
            
        lines = ["classDiagram"]
        for cls in self.classes:
            lines.append(f"    class {cls}")
            
        for base, derived in self.relationships:
            # Mermaid syntax for inheritance
            lines.append(f"    {base} <|-- {derived}")
            
        return "\\n".join(lines)


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        logger.info("--- Testing DatasheetAutoSummarizer ---")
        summarizer = DatasheetAutoSummarizer()
        sample_datasheet_text = """
        The ESP32 is a low-power system on a chip (SoC).
        Operating Voltage: 3.3V
        Peak Power Consumption: 500mW
        Feature: Supports Wi-Fi and Bluetooth
        """
        spec = await summarizer.summarize_text(sample_datasheet_text, "ESP32-WROOM-32")
        logger.info(f"Extracted Spec: {spec.model_dump_json(indent=2)}")
        
        logger.info("\\n--- Testing ArchitectureGraphVisualizer ---")
        visualizer = ArchitectureGraphVisualizer()
        
        sample_code = """
class BaseSensor:
    pass

class TemperatureSensor(BaseSensor):
    pass

class HumiditySensor(BaseSensor):
    pass
"""
        mermaid_code = visualizer.generate_mermaid_diagram(sample_code)
        logger.info(f"Generated Mermaid Diagram:\\n{mermaid_code}")

    asyncio.run(run_tests())
