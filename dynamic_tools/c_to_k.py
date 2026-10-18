"""
Purpose: Utility to convert temperature from Celsius to Kelvin
Created: 2026-10-09 14:24:39.984562
"""

def c_to_k(temp_c):
    """Convert temperature from Celsius to Kelvin."""
    try:
        celsius = float(temp_c)
        kelvin = celsius + 273.15
        if kelvin < 0:
            raise ValueError("Temperature below absolute zero.")
        return kelvin
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid temperature input: {e}") from e