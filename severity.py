from PIL import Image


PROTOTYPE_SEVERITY_SOURCE = "prototype_visual_coverage"


def estimate_severity(image: Image.Image, problem: str) -> dict[str, str | float]:
    """Estimate visible symptom coverage; this is not an expert severity label."""
    if problem == "uncertain":
        return {
            "severity": "unknown",
            "severity_source": "unavailable",
            "visible_damage_fraction": 0.0,
        }
    if problem == "healthy":
        return {
            "severity": "low",
            "severity_source": PROTOTYPE_SEVERITY_SOURCE,
            "visible_damage_fraction": 0.0,
        }

    pixels = image.convert("RGB").resize((224, 224)).tobytes()
    green_tissue = []
    symptom_pixels = []
    for offset in range(0, len(pixels), 3):
        red, green, blue = pixels[offset : offset + 3]
        maximum = max(red, green, blue)
        minimum = min(red, green, blue)
        green_tissue.append(
            green > red * 1.05 and green > blue * 0.90 and green > 45
        )
        yellow = (
            red > 70
            and green > 65
            and green > blue * 1.15
            and abs(red - green) < 75
        )
        brown = (
            red > green * 1.10
            and green > blue * 1.05
            and red > 45
        )
        white = minimum > 185 and maximum - minimum < 45
        dark = maximum < 50
        gray = 65 < maximum < 190 and maximum - minimum < 35
        if problem in {"spider_mite", "thrips", "downy_mildew"}:
            symptom_pixels.append(yellow or brown)
        elif problem == "powdery_mildew":
            symptom_pixels.append(white or brown)
        elif problem == "grey_mould":
            symptom_pixels.append(white or gray or brown)
        elif problem == "black_spot":
            symptom_pixels.append(brown or dark)
        else:
            return {
                "severity": "unknown",
                "severity_source": "unavailable",
                "visible_damage_fraction": 0.0,
            }

    total_pixels = len(pixels) // 3
    if not total_pixels:
        return {
            "severity": "unknown",
            "severity_source": "unavailable",
            "visible_damage_fraction": 0.0,
        }

    plant_pixel_count = sum(
        green or symptom for green, symptom in zip(green_tissue, symptom_pixels)
    )
    green_pixel_count = sum(green_tissue)
    if plant_pixel_count < total_pixels * 0.08 or (
        plant_pixel_count > total_pixels * 0.95
        and green_pixel_count < total_pixels * 0.05
    ):
        return {
            "severity": "unknown",
            "severity_source": "unavailable",
            "visible_damage_fraction": 0.0,
        }

    damaged_count = sum(
        symptom and (green or symptom)
        for green, symptom in zip(green_tissue, symptom_pixels)
    )
    fraction = damaged_count / plant_pixel_count
    severity = "low" if fraction < 0.05 else "medium" if fraction < 0.20 else "high"
    return {
        "severity": severity,
        "severity_source": PROTOTYPE_SEVERITY_SOURCE,
        "visible_damage_fraction": round(fraction, 4),
    }
