"""HEI-2020 and HEI-Toddlers-2020, ported from dietaryindex 2.1.

See reference/dietaryindex for the frozen R algorithms and attribution.
No population adjustment or usual-intake estimation is performed.
"""
import math

REFERENCE = {"package": "dietaryindex", "version": "2.1",
             "commit": "0cb60bd67c2942d954d20637500c4a921a935f51"}
FIELDS = ("age", "kcal", "total_fruit", "whole_fruit", "total_vegetable",
          "green_and_bean", "total_protein", "seafood_plant_protein", "whole_grain",
          "dairy", "fatty_acid", "refined_grain", "sodium", "added_sugar", "saturated_fat")
COMPONENTS = ("TOTALFRT", "FRT", "VEG", "GREENNBEAN", "TOTALPRO", "SEAPLANTPRO",
              "WHOLEGRAIN", "DAIRY", "FATTYACID", "REFINEDGRAIN", "SODIUM", "ADDEDSUGAR", "SATFAT")


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return float(value)


def _increasing(value, low, high, points):
    if value >= high:
        return float(points)
    if value <= low:
        return 0.0
    return (value-low)*points/(high-low)


def _decreasing(value, bad, good):
    if value >= bad:
        return 0.0
    if value <= good:
        return 10.0
    return (value-bad)*10/(good-bad)


def hei2020_from_percent(inputs):
    """Match R HEI2020: cups/oz equivalents, sodium g, sugar/satfat % kcal.

    fatty_acid is (MUFA+PUFA)/SFA. Positive energy and age >=1 are
    required; undefined ratios must be resolved before calling this function.
    """
    if not isinstance(inputs,dict):
        raise ValueError('inputs must be an object')
    for key in FIELDS:
        if inputs.get(key) is not None:
            _number(inputs[key],key)
    if inputs.get('age') is not None and inputs['age']<1:
        raise ValueError('HEI-2020 is not defined for age under 1 year')
    if inputs.get('kcal') is not None and inputs['kcal']<=0:
        raise ValueError('HEI-2020 requires positive total energy')
    missing = [key for key in FIELDS if inputs.get(key) is None]
    if missing:
        return {"status": "partial", "total": None, "components": {}, "missing": missing,
                "reference": dict(REFERENCE, function="HEI2020")}
    x = {key: _number(inputs[key], key) for key in FIELDS}
    if x["age"] < 1:
        raise ValueError("HEI-2020 is not defined for age under 1 year")
    if x["kcal"] <= 0:
        raise ValueError("HEI-2020 requires positive total energy")
    toddler = x["age"] < 2
    density = x["kcal"]/1000
    targets = (0.7, 0.3, 0.9, 0.1, 2, 0.5, 1.5, 2) if toddler else (0.8, 0.4, 1.1, 0.2, 2.5, 0.8, 1.5, 1.3)
    fields = FIELDS[2:10]
    values = [_increasing(x[key]/density, 0, target, 5 if i < 6 else 10)
              for i, (key, target) in enumerate(zip(fields, targets))]
    values.append(_increasing(x["fatty_acid"], 0.9 if toddler else 1.2, 1.5 if toddler else 2.5, 10))
    values.extend([
        _decreasing(x["refined_grain"]/density, 3.4 if toddler else 4.3, 1.5 if toddler else 1.8),
        _decreasing(x["sodium"]/density, 1.7 if toddler else 2.0, 1.1),
        _decreasing(x["added_sugar"], 13.8 if toddler else 26, 0 if toddler else 6.5),
        _decreasing(x["saturated_fat"], 18.2 if toddler else 16, 12.2 if toddler else 8),
    ])
    return {"status": "complete", "total": sum(values),
            "components": {"HEI2020_"+name: value for name, value in zip(COMPONENTS, values)},
            "missing": [], "index": "HEI-Toddlers-2020" if toddler else "HEI-2020",
            "reference": dict(REFERENCE, function="HEI2020")}


def hei2020(inputs):
    """Match R HEI2020_V2: sodium mg, added sugar tsp equivalents, SFA g.

    Food groups use cup/oz equivalents. Added sugar is converted with the
    frozen R method (4g/tsp x 4kcal/g), not a substituted 4.2g conversion.
    """
    if not isinstance(inputs,dict):
        raise ValueError('inputs must be an object')
    x = dict(inputs)
    for key in FIELDS:
        if x.get(key) is not None:
            _number(x[key], key)
    if x.get("age") is not None and x["age"] < 1:
        raise ValueError("HEI-2020 is not defined for age under 1 year")
    if x.get("kcal") is not None:
        if x["kcal"] <= 0:
            raise ValueError("HEI-2020 requires positive total energy")
        for key, factor in (("added_sugar", 16), ("saturated_fat", 9)):
            if x.get(key) is not None:
                x[key] = x[key]*factor/x["kcal"]*100
    if x.get("sodium") is not None:
        x["sodium"] /= 1000
    result = hei2020_from_percent(x)
    result["reference"]["function"] = "HEI2020_V2"
    return result
