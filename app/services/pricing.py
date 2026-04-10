from typing import Any

from app.config import settings
from app.models.tables import Filament
from app.services.gcode_parser import parse_time_to_hours
from app.utils.errors import SlicerError


def calculate_cost(
    parsed_gcode: dict[str, Any],
    filament: Filament,
    machine_rate: float | None = None,
    markup: float | None = None,
) -> dict[str, Any]:
    """Calculate full cost breakdown for a sliced part.

    - Uses parsed filament grams if present, otherwise filament_cm3 * density.
    - machine_rate and markup fall back to env defaults when not supplied.
    - All monetary values are rounded to 4 decimal places.
    """
    if machine_rate is None:
        machine_rate = settings.DEFAULT_MACHINE_RATE_PER_HOUR
    if markup is None:
        markup = settings.DEFAULT_MARKUP_MULTIPLIER

    density = float(filament.density_g_per_cm3)
    cost_per_kg = float(filament.cost_per_kg)

    filament_g = parsed_gcode.get("filament_g")
    filament_cm3 = parsed_gcode.get("filament_cm3")

    if filament_g is None and filament_cm3 is not None:
        filament_g = filament_cm3 * density

    if filament_g is None:
        raise SlicerError(message="Could not determine filament usage")

    print_time_hours = parsed_gcode.get("estimated_print_time_hours")
    if print_time_hours is None:
        print_time_hours = parse_time_to_hours(parsed_gcode.get("estimated_print_time")) or 0.0

    material_cost = (filament_g / 1000.0) * cost_per_kg
    machine_cost = print_time_hours * machine_rate
    total_cost = material_cost + machine_cost
    customer_price = total_cost * markup

    return {
        "pricing": {
            "material_cost": round(material_cost, 4),
            "machine_cost": round(machine_cost, 4),
            "total_cost": round(total_cost, 4),
            "customer_price": round(customer_price, 4),
            "currency": "USD",
        },
        "details": {
            "filament_type": filament.type,
            "cost_per_kg": round(cost_per_kg, 4),
            "density_g_per_cm3": round(density, 4),
            "machine_rate_per_hour": round(float(machine_rate), 4),
            "markup_multiplier": round(float(markup), 4),
        },
        "filament_grams": round(filament_g, 4),
        "print_time_hours": round(print_time_hours, 4),
    }
