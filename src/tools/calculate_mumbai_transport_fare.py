from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Literal, Optional, Set, Tuple

from app import mcp
from thefuzz import process


FareVariant = Literal["old", "revised"]
TimePeriod = Literal["normal", "midnight"]
FareMode = Literal["road", "metro"]


@dataclass(frozen=True)
class FareRecord:
    vehicle_type: str
    distance_km: float
    old_normal: float
    revised_normal: float
    old_midnight: float
    revised_midnight: float


@lru_cache(maxsize=1)
def _load_fare_table() -> Dict[str, Dict[float, FareRecord]]:
    table: Dict[str, Dict[float, FareRecord]] = {}
    fares_path = Path(__file__).parent / "data" / "fares.csv"
    if not fares_path.exists():
        raise FileNotFoundError(f"data/fares.csv not found at {fares_path}")

    with fares_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            try:
                vehicle_type = row["VehicleType"].strip()
                distance_km = float(row["Distance_KM"])
                old_normal = float(row["OldFare_Normal_RS"])
                revised_normal = float(row["RevisedFare_Normal_RS"])
                old_midnight = float(row["OldFare_Midnight_RS"])
                revised_midnight = float(row["RevisedFare_Midnight_RS"])
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Invalid fare row: {row}") from exc

            vehicle_bucket = table.setdefault(vehicle_type.lower(), {})
            vehicle_bucket[round(distance_km, 2)] = FareRecord(
                vehicle_type=vehicle_type,
                distance_km=distance_km,
                old_normal=old_normal,
                revised_normal=revised_normal,
                old_midnight=old_midnight,
                revised_midnight=revised_midnight,
            )

    return table


def _select_fare(
    record: FareRecord, variant: FareVariant, time_period: TimePeriod
) -> float:
    if variant == "old" and time_period == "normal":
        return record.old_normal
    if variant == "old" and time_period == "midnight":
        return record.old_midnight
    if variant == "revised" and time_period == "normal":
        return record.revised_normal
    return record.revised_midnight


LINE_1_STATIONS = [
    "Versova",
    "DN Nagar",
    "Azad Nagar",
    "Andheri",
    "Western Express Highway",
    "Chakala",
    "Airport Road",
    "Marol Naka",
    "Saki Naka",
    "Asalfa",
    "Jagruti Nagar",
    "Ghatkopar",
]

LINE_1_FARES = {
    "Versova": {
        "Versova": 10,
        "DN Nagar": 10,
        "Azad Nagar": 20,
        "Andheri": 20,
        "Western Express Highway": 20,
        "Chakala": 30,
        "Airport Road": 30,
        "Marol Naka": 30,
        "Saki Naka": 30,
        "Asalfa": 40,
        "Jagruti Nagar": 40,
        "Ghatkopar": 40,
    },
    "DN Nagar": {
        "Versova": 10,
        "DN Nagar": 10,
        "Azad Nagar": 10,
        "Andheri": 20,
        "Western Express Highway": 20,
        "Chakala": 20,
        "Airport Road": 30,
        "Marol Naka": 30,
        "Saki Naka": 30,
        "Asalfa": 40,
        "Jagruti Nagar": 40,
        "Ghatkopar": 40,
    },
    "Azad Nagar": {
        "Versova": 20,
        "DN Nagar": 10,
        "Azad Nagar": 10,
        "Andheri": 10,
        "Western Express Highway": 20,
        "Chakala": 20,
        "Airport Road": 20,
        "Marol Naka": 30,
        "Saki Naka": 30,
        "Asalfa": 30,
        "Jagruti Nagar": 40,
        "Ghatkopar": 40,
    },
    "Andheri": {
        "Versova": 20,
        "DN Nagar": 20,
        "Azad Nagar": 10,
        "Andheri": 10,
        "Western Express Highway": 10,
        "Chakala": 20,
        "Airport Road": 20,
        "Marol Naka": 20,
        "Saki Naka": 20,
        "Asalfa": 30,
        "Jagruti Nagar": 30,
        "Ghatkopar": 30,
    },
    "Western Express Highway": {
        "Versova": 20,
        "DN Nagar": 20,
        "Azad Nagar": 20,
        "Andheri": 10,
        "Western Express Highway": 10,
        "Chakala": 10,
        "Airport Road": 20,
        "Marol Naka": 20,
        "Saki Naka": 20,
        "Asalfa": 30,
        "Jagruti Nagar": 30,
        "Ghatkopar": 30,
    },
    "Chakala": {
        "Versova": 30,
        "DN Nagar": 20,
        "Azad Nagar": 20,
        "Andheri": 20,
        "Western Express Highway": 10,
        "Chakala": 10,
        "Airport Road": 10,
        "Marol Naka": 10,
        "Saki Naka": 20,
        "Asalfa": 20,
        "Jagruti Nagar": 20,
        "Ghatkopar": 30,
    },
    "Airport Road": {
        "Versova": 30,
        "DN Nagar": 30,
        "Azad Nagar": 20,
        "Andheri": 20,
        "Western Express Highway": 20,
        "Chakala": 10,
        "Airport Road": 10,
        "Marol Naka": 10,
        "Saki Naka": 10,
        "Asalfa": 20,
        "Jagruti Nagar": 20,
        "Ghatkopar": 20,
    },
    "Marol Naka": {
        "Versova": 30,
        "DN Nagar": 30,
        "Azad Nagar": 30,
        "Andheri": 20,
        "Western Express Highway": 20,
        "Chakala": 10,
        "Airport Road": 10,
        "Marol Naka": 10,
        "Saki Naka": 10,
        "Asalfa": 10,
        "Jagruti Nagar": 20,
        "Ghatkopar": 20,
    },
    "Saki Naka": {
        "Versova": 30,
        "DN Nagar": 30,
        "Azad Nagar": 30,
        "Andheri": 20,
        "Western Express Highway": 20,
        "Chakala": 20,
        "Airport Road": 10,
        "Marol Naka": 10,
        "Saki Naka": 10,
        "Asalfa": 10,
        "Jagruti Nagar": 10,
        "Ghatkopar": 20,
    },
    "Asalfa": {
        "Versova": 40,
        "DN Nagar": 40,
        "Azad Nagar": 30,
        "Andheri": 30,
        "Western Express Highway": 30,
        "Chakala": 20,
        "Airport Road": 20,
        "Marol Naka": 10,
        "Saki Naka": 10,
        "Asalfa": 10,
        "Jagruti Nagar": 10,
        "Ghatkopar": 10,
    },
    "Jagruti Nagar": {
        "Versova": 40,
        "DN Nagar": 40,
        "Azad Nagar": 40,
        "Andheri": 30,
        "Western Express Highway": 30,
        "Chakala": 20,
        "Airport Road": 20,
        "Marol Naka": 20,
        "Saki Naka": 10,
        "Asalfa": 10,
        "Jagruti Nagar": 10,
        "Ghatkopar": 10,
    },
    "Ghatkopar": {
        "Versova": 40,
        "DN Nagar": 40,
        "Azad Nagar": 40,
        "Andheri": 30,
        "Western Express Highway": 30,
        "Chakala": 30,
        "Airport Road": 20,
        "Marol Naka": 20,
        "Saki Naka": 20,
        "Asalfa": 10,
        "Jagruti Nagar": 10,
        "Ghatkopar": 10,
    },
}


LINE_2A_7_STATIONS = [
    "Gundavali",
    "Mogra",
    "Jogeshwari (East)",
    "Goregaon (East)",
    "Aarey",
    "Dindoshi",
    "Kurar",
    "Akurli",
    "Poisar",
    "Magathane",
    "Devipada",
    "Rashtriya Udyan",
    "Ovripada",
    "Dahisar (East)",
    "Anand Nagar",
    "Kandarpada",
    "Mandapeshwar",
    "Eksar",
    "Borivali (West)",
    "Pahadi Eksar",
    "Kandivali (West)",
    "Dahanukarwadi",
    "Valnai",
    "Malad (West)",
    "Lower Malad",
    "Pahadi Goregaon",
    "Goregaon (West)",
    "Oshiwara",
    "Lower Oshiwara",
    "DN Nagar",
]

LINE_2A_7_FARES = {
    "Gundavali": {
        "Gundavali": 10,
        "Mogra": 10,
        "Jogeshwari (East)": 20,
        "Goregaon (East)": 20,
        "Aarey": 20,
        "Dindoshi": 20,
        "Kurar": 20,
        "Akurli": 20,
        "Poisar": 20,
        "Magathane": 20,
        "Devipada": 30,
        "Rashtriya Udyan": 30,
        "Ovripada": 30,
        "Dahisar (East)": 30,
        "Anand Nagar": 30,
        "Kandarpada": 40,
        "Mandapeshwar": 40,
        "Eksar": 40,
        "Borivali (West)": 40,
        "Pahadi Eksar": 40,
        "Kandivali (West)": 40,
        "Dahanukarwadi": 50,
        "Valnai": 50,
        "Malad (West)": 50,
        "Lower Malad": 50,
        "Pahadi Goregaon": 50,
        "Goregaon (West)": 60,
        "Oshiwara": 60,
        "Lower Oshiwara": 60,
        "DN Nagar": 60,
    },
    "Mogra": {
        "Gundavali": 10,
        "Mogra": 10,
        "Jogeshwari (East)": 10,
        "Goregaon (East)": 20,
        "Aarey": 20,
        "Dindoshi": 20,
        "Kurar": 20,
        "Akurli": 20,
        "Poisar": 20,
        "Magathane": 20,
        "Devipada": 20,
        "Rashtriya Udyan": 30,
        "Ovripada": 30,
        "Dahisar (East)": 30,
        "Anand Nagar": 30,
        "Kandarpada": 30,
        "Mandapeshwar": 40,
        "Eksar": 40,
        "Borivali (West)": 40,
        "Pahadi Eksar": 40,
        "Kandivali (West)": 40,
        "Dahanukarwadi": 40,
        "Valnai": 50,
        "Malad (West)": 50,
        "Lower Malad": 50,
        "Pahadi Goregaon": 50,
        "Goregaon (West)": 50,
        "Oshiwara": 60,
        "Lower Oshiwara": 60,
        "DN Nagar": 60,
    },
    "Jogeshwari (East)": {
        "Gundavali": 20,
        "Mogra": 10,
        "Jogeshwari (East)": 10,
        "Goregaon (East)": 10,
        "Aarey": 10,
        "Dindoshi": 20,
        "Kurar": 20,
        "Akurli": 20,
        "Poisar": 20,
        "Magathane": 20,
        "Devipada": 20,
        "Rashtriya Udyan": 20,
        "Ovripada": 30,
        "Dahisar (East)": 30,
        "Anand Nagar": 30,
        "Kandarpada": 30,
        "Mandapeshwar": 30,
        "Eksar": 30,
        "Borivali (West)": 40,
        "Pahadi Eksar": 40,
        "Kandivali (West)": 40,
        "Dahanukarwadi": 40,
        "Valnai": 40,
        "Malad (West)": 40,
        "Lower Malad": 50,
        "Pahadi Goregaon": 50,
        "Goregaon (West)": 50,
        "Oshiwara": 50,
        "Lower Oshiwara": 50,
        "DN Nagar": 60,
    },
    "Goregaon (East)": {
        "Gundavali": 20,
        "Mogra": 20,
        "Jogeshwari (East)": 10,
        "Goregaon (East)": 10,
        "Aarey": 10,
        "Dindoshi": 10,
        "Kurar": 20,
        "Akurli": 20,
        "Poisar": 20,
        "Magathane": 20,
        "Devipada": 20,
        "Rashtriya Udyan": 20,
        "Ovripada": 20,
        "Dahisar (East)": 30,
        "Anand Nagar": 30,
        "Kandarpada": 30,
        "Mandapeshwar": 30,
        "Eksar": 30,
        "Borivali (West)": 30,
        "Pahadi Eksar": 40,
        "Kandivali (West)": 40,
        "Dahanukarwadi": 40,
        "Valnai": 40,
        "Malad (West)": 40,
        "Lower Malad": 40,
        "Pahadi Goregaon": 50,
        "Goregaon (West)": 50,
        "Oshiwara": 50,
        "Lower Oshiwara": 50,
        "DN Nagar": 50,
    },
    "Aarey": {
        "Gundavali": 20,
        "Mogra": 20,
        "Jogeshwari (East)": 10,
        "Goregaon (East)": 10,
        "Aarey": 10,
        "Dindoshi": 10,
        "Kurar": 10,
        "Akurli": 20,
        "Poisar": 20,
        "Magathane": 20,
        "Devipada": 20,
        "Rashtriya Udyan": 20,
        "Ovripada": 20,
        "Dahisar (East)": 20,
        "Anand Nagar": 30,
        "Kandarpada": 30,
        "Mandapeshwar": 30,
        "Eksar": 30,
        "Borivali (West)": 30,
        "Pahadi Eksar": 30,
        "Kandivali (West)": 40,
        "Dahanukarwadi": 40,
        "Valnai": 40,
        "Malad (West)": 40,
        "Lower Malad": 40,
        "Pahadi Goregaon": 40,
        "Goregaon (West)": 50,
        "Oshiwara": 50,
        "Lower Oshiwara": 50,
        "DN Nagar": 50,
    },
    "Dindoshi": {
        "Gundavali": 20,
        "Mogra": 20,
        "Jogeshwari (East)": 20,
        "Goregaon (East)": 10,
        "Aarey": 10,
        "Dindoshi": 10,
        "Kurar": 10,
        "Akurli": 10,
        "Poisar": 20,
        "Magathane": 20,
        "Devipada": 20,
        "Rashtriya Udyan": 20,
        "Ovripada": 20,
        "Dahisar (East)": 20,
        "Anand Nagar": 20,
        "Kandarpada": 30,
        "Mandapeshwar": 30,
        "Eksar": 30,
        "Borivali (West)": 30,
        "Pahadi Eksar": 30,
        "Kandivali (West)": 30,
        "Dahanukarwadi": 40,
        "Valnai": 40,
        "Malad (West)": 40,
        "Lower Malad": 40,
        "Pahadi Goregaon": 40,
        "Goregaon (West)": 40,
        "Oshiwara": 50,
        "Lower Oshiwara": 50,
        "DN Nagar": 50,
    },
    "Kurar": {
        "Gundavali": 20,
        "Mogra": 20,
        "Jogeshwari (East)": 20,
        "Goregaon (East)": 20,
        "Aarey": 10,
        "Dindoshi": 10,
        "Kurar": 10,
        "Akurli": 10,
        "Poisar": 10,
        "Magathane": 20,
        "Devipada": 20,
        "Rashtriya Udyan": 20,
        "Ovripada": 20,
        "Dahisar (East)": 20,
        "Anand Nagar": 20,
        "Kandarpada": 20,
        "Mandapeshwar": 30,
        "Eksar": 30,
        "Borivali (West)": 30,
        "Pahadi Eksar": 30,
        "Kandivali (West)": 30,
        "Dahanukarwadi": 30,
        "Valnai": 40,
        "Malad (West)": 40,
        "Lower Malad": 40,
        "Pahadi Goregaon": 40,
        "Goregaon (West)": 40,
        "Oshiwara": 40,
        "Lower Oshiwara": 50,
        "DN Nagar": 50,
    },
    "Akurli": {
        "Gundavali": 20,
        "Mogra": 20,
        "Jogeshwari (East)": 20,
        "Goregaon (East)": 20,
        "Aarey": 20,
        "Dindoshi": 10,
        "Kurar": 10,
        "Akurli": 10,
        "Poisar": 10,
        "Magathane": 10,
        "Devipada": 10,
        "Rashtriya Udyan": 20,
        "Ovripada": 20,
        "Dahisar (East)": 20,
        "Anand Nagar": 20,
        "Kandarpada": 20,
        "Mandapeshwar": 20,
        "Eksar": 30,
        "Borivali (West)": 30,
        "Pahadi Eksar": 30,
        "Kandivali (West)": 30,
        "Dahanukarwadi": 30,
        "Valnai": 30,
        "Malad (West)": 30,
        "Lower Malad": 40,
        "Pahadi Goregaon": 40,
        "Goregaon (West)": 40,
        "Oshiwara": 40,
        "Lower Oshiwara": 40,
        "DN Nagar": 40,
    },
    "Poisar": {
        "Gundavali": 20,
        "Mogra": 20,
        "Jogeshwari (East)": 20,
        "Goregaon (East)": 20,
        "Aarey": 20,
        "Dindoshi": 20,
        "Kurar": 10,
        "Akurli": 10,
        "Poisar": 10,
        "Magathane": 10,
        "Devipada": 10,
        "Rashtriya Udyan": 10,
        "Ovripada": 20,
        "Dahisar (East)": 20,
        "Anand Nagar": 20,
        "Kandarpada": 20,
        "Mandapeshwar": 20,
        "Eksar": 20,
        "Borivali (West)": 30,
        "Pahadi Eksar": 30,
        "Kandivali (West)": 30,
        "Dahanukarwadi": 30,
        "Valnai": 30,
        "Malad (West)": 30,
        "Lower Malad": 30,
        "Pahadi Goregaon": 40,
        "Goregaon (West)": 40,
        "Oshiwara": 40,
        "Lower Oshiwara": 40,
        "DN Nagar": 40,
    },
    "Magathane": {
        "Gundavali": 20,
        "Mogra": 20,
        "Jogeshwari (East)": 20,
        "Goregaon (East)": 20,
        "Aarey": 20,
        "Dindoshi": 20,
        "Kurar": 20,
        "Akurli": 10,
        "Poisar": 10,
        "Magathane": 10,
        "Devipada": 10,
        "Rashtriya Udyan": 10,
        "Ovripada": 10,
        "Dahisar (East)": 20,
        "Anand Nagar": 20,
        "Kandarpada": 20,
        "Mandapeshwar": 20,
        "Eksar": 20,
        "Borivali (West)": 20,
        "Pahadi Eksar": 30,
        "Kandivali (West)": 30,
        "Dahanukarwadi": 30,
        "Valnai": 30,
        "Malad (West)": 30,
        "Lower Malad": 30,
        "Pahadi Goregaon": 30,
        "Goregaon (West)": 40,
        "Oshiwara": 40,
        "Lower Oshiwara": 40,
        "DN Nagar": 40,
    },
    "Devipada": {
        "Gundavali": 30,
        "Mogra": 20,
        "Jogeshwari (East)": 20,
        "Goregaon (East)": 20,
        "Aarey": 20,
        "Dindoshi": 20,
        "Kurar": 20,
        "Akurli": 10,
        "Poisar": 10,
        "Magathane": 10,
        "Devipada": 10,
        "Rashtriya Udyan": 10,
        "Ovripada": 10,
        "Dahisar (East)": 10,
        "Anand Nagar": 20,
        "Kandarpada": 20,
        "Mandapeshwar": 20,
        "Eksar": 20,
        "Borivali (West)": 20,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 30,
        "Dahanukarwadi": 30,
        "Valnai": 30,
        "Malad (West)": 30,
        "Lower Malad": 30,
        "Pahadi Goregaon": 30,
        "Goregaon (West)": 30,
        "Oshiwara": 40,
        "Lower Oshiwara": 40,
        "DN Nagar": 40,
    },
    "Rashtriya Udyan": {
        "Gundavali": 30,
        "Mogra": 30,
        "Jogeshwari (East)": 20,
        "Goregaon (East)": 20,
        "Aarey": 20,
        "Dindoshi": 20,
        "Kurar": 20,
        "Akurli": 20,
        "Poisar": 10,
        "Magathane": 10,
        "Devipada": 10,
        "Rashtriya Udyan": 10,
        "Ovripada": 10,
        "Dahisar (East)": 10,
        "Anand Nagar": 10,
        "Kandarpada": 20,
        "Mandapeshwar": 20,
        "Eksar": 20,
        "Borivali (West)": 20,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 30,
        "Valnai": 30,
        "Malad (West)": 30,
        "Lower Malad": 30,
        "Pahadi Goregaon": 30,
        "Goregaon (West)": 30,
        "Oshiwara": 30,
        "Lower Oshiwara": 40,
        "DN Nagar": 40,
    },
    "Ovripada": {
        "Gundavali": 30,
        "Mogra": 30,
        "Jogeshwari (East)": 30,
        "Goregaon (East)": 20,
        "Aarey": 20,
        "Dindoshi": 20,
        "Kurar": 20,
        "Akurli": 20,
        "Poisar": 20,
        "Magathane": 10,
        "Devipada": 10,
        "Rashtriya Udyan": 10,
        "Ovripada": 10,
        "Dahisar (East)": 10,
        "Anand Nagar": 10,
        "Kandarpada": 10,
        "Mandapeshwar": 20,
        "Eksar": 20,
        "Borivali (West)": 20,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 20,
        "Valnai": 30,
        "Malad (West)": 30,
        "Lower Malad": 30,
        "Pahadi Goregaon": 30,
        "Goregaon (West)": 30,
        "Oshiwara": 30,
        "Lower Oshiwara": 30,
        "DN Nagar": 40,
    },
    "Dahisar (East)": {
        "Gundavali": 30,
        "Mogra": 30,
        "Jogeshwari (East)": 30,
        "Goregaon (East)": 30,
        "Aarey": 20,
        "Dindoshi": 20,
        "Kurar": 20,
        "Akurli": 20,
        "Poisar": 20,
        "Magathane": 20,
        "Devipada": 10,
        "Rashtriya Udyan": 10,
        "Ovripada": 10,
        "Dahisar (East)": 10,
        "Anand Nagar": 10,
        "Kandarpada": 10,
        "Mandapeshwar": 10,
        "Eksar": 20,
        "Borivali (West)": 20,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 20,
        "Valnai": 20,
        "Malad (West)": 30,
        "Lower Malad": 30,
        "Pahadi Goregaon": 30,
        "Goregaon (West)": 30,
        "Oshiwara": 30,
        "Lower Oshiwara": 30,
        "DN Nagar": 30,
    },
    "Anand Nagar": {
        "Gundavali": 30,
        "Mogra": 30,
        "Jogeshwari (East)": 30,
        "Goregaon (East)": 30,
        "Aarey": 30,
        "Dindoshi": 20,
        "Kurar": 20,
        "Akurli": 20,
        "Poisar": 20,
        "Magathane": 20,
        "Devipada": 20,
        "Rashtriya Udyan": 10,
        "Ovripada": 10,
        "Dahisar (East)": 10,
        "Anand Nagar": 10,
        "Kandarpada": 10,
        "Mandapeshwar": 10,
        "Eksar": 10,
        "Borivali (West)": 20,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 20,
        "Valnai": 20,
        "Malad (West)": 20,
        "Lower Malad": 30,
        "Pahadi Goregaon": 30,
        "Goregaon (West)": 30,
        "Oshiwara": 30,
        "Lower Oshiwara": 30,
        "DN Nagar": 30,
    },
    "Kandarpada": {
        "Gundavali": 40,
        "Mogra": 30,
        "Jogeshwari (East)": 30,
        "Goregaon (East)": 30,
        "Aarey": 30,
        "Dindoshi": 30,
        "Kurar": 20,
        "Akurli": 20,
        "Poisar": 20,
        "Magathane": 20,
        "Devipada": 20,
        "Rashtriya Udyan": 20,
        "Ovripada": 10,
        "Dahisar (East)": 10,
        "Anand Nagar": 10,
        "Kandarpada": 10,
        "Mandapeshwar": 10,
        "Eksar": 10,
        "Borivali (West)": 10,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 20,
        "Valnai": 20,
        "Malad (West)": 20,
        "Lower Malad": 20,
        "Pahadi Goregaon": 30,
        "Goregaon (West)": 30,
        "Oshiwara": 30,
        "Lower Oshiwara": 30,
        "DN Nagar": 30,
    },
    "Mandapeshwar": {
        "Gundavali": 40,
        "Mogra": 40,
        "Jogeshwari (East)": 30,
        "Goregaon (East)": 30,
        "Aarey": 30,
        "Dindoshi": 30,
        "Kurar": 30,
        "Akurli": 20,
        "Poisar": 20,
        "Magathane": 20,
        "Devipada": 20,
        "Rashtriya Udyan": 20,
        "Ovripada": 20,
        "Dahisar (East)": 10,
        "Anand Nagar": 10,
        "Kandarpada": 10,
        "Mandapeshwar": 10,
        "Eksar": 10,
        "Borivali (West)": 10,
        "Pahadi Eksar": 10,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 20,
        "Valnai": 20,
        "Malad (West)": 20,
        "Lower Malad": 20,
        "Pahadi Goregaon": 20,
        "Goregaon (West)": 30,
        "Oshiwara": 30,
        "Lower Oshiwara": 30,
        "DN Nagar": 30,
    },
    "Eksar": {
        "Gundavali": 40,
        "Mogra": 40,
        "Jogeshwari (East)": 30,
        "Goregaon (East)": 30,
        "Aarey": 30,
        "Dindoshi": 30,
        "Kurar": 30,
        "Akurli": 30,
        "Poisar": 20,
        "Magathane": 20,
        "Devipada": 20,
        "Rashtriya Udyan": 20,
        "Ovripada": 20,
        "Dahisar (East)": 20,
        "Anand Nagar": 10,
        "Kandarpada": 10,
        "Mandapeshwar": 10,
        "Eksar": 10,
        "Borivali (West)": 10,
        "Pahadi Eksar": 10,
        "Kandivali (West)": 10,
        "Dahanukarwadi": 20,
        "Valnai": 20,
        "Malad (West)": 20,
        "Lower Malad": 20,
        "Pahadi Goregaon": 20,
        "Goregaon (West)": 20,
        "Oshiwara": 30,
        "Lower Oshiwara": 30,
        "DN Nagar": 30,
    },
    "Borivali (West)": {
        "Gundavali": 40,
        "Mogra": 40,
        "Jogeshwari (East)": 40,
        "Goregaon (East)": 30,
        "Aarey": 30,
        "Dindoshi": 30,
        "Kurar": 30,
        "Akurli": 30,
        "Poisar": 30,
        "Magathane": 20,
        "Devipada": 20,
        "Rashtriya Udyan": 20,
        "Ovripada": 20,
        "Dahisar (East)": 20,
        "Anand Nagar": 20,
        "Kandarpada": 10,
        "Mandapeshwar": 10,
        "Eksar": 10,
        "Borivali (West)": 10,
        "Pahadi Eksar": 10,
        "Kandivali (West)": 10,
        "Dahanukarwadi": 10,
        "Valnai": 20,
        "Malad (West)": 20,
        "Lower Malad": 20,
        "Pahadi Goregaon": 20,
        "Goregaon (West)": 20,
        "Oshiwara": 20,
        "Lower Oshiwara": 30,
        "DN Nagar": 20,
    },
    "Pahadi Eksar": {
        "Gundavali": 40,
        "Mogra": 40,
        "Jogeshwari (East)": 40,
        "Goregaon (East)": 40,
        "Aarey": 30,
        "Dindoshi": 30,
        "Kurar": 30,
        "Akurli": 30,
        "Poisar": 30,
        "Magathane": 30,
        "Devipada": 20,
        "Rashtriya Udyan": 20,
        "Ovripada": 20,
        "Dahisar (East)": 20,
        "Anand Nagar": 20,
        "Kandarpada": 20,
        "Mandapeshwar": 10,
        "Eksar": 10,
        "Borivali (West)": 10,
        "Pahadi Eksar": 10,
        "Kandivali (West)": 10,
        "Dahanukarwadi": 10,
        "Valnai": 10,
        "Malad (West)": 20,
        "Lower Malad": 20,
        "Pahadi Goregaon": 20,
        "Goregaon (West)": 20,
        "Oshiwara": 20,
        "Lower Oshiwara": 20,
        "DN Nagar": 20,
    },
    "Kandivali (West)": {
        "Gundavali": 40,
        "Mogra": 40,
        "Jogeshwari (East)": 40,
        "Goregaon (East)": 40,
        "Aarey": 40,
        "Dindoshi": 30,
        "Kurar": 30,
        "Akurli": 30,
        "Poisar": 30,
        "Magathane": 30,
        "Devipada": 30,
        "Rashtriya Udyan": 20,
        "Ovripada": 20,
        "Dahisar (East)": 20,
        "Anand Nagar": 20,
        "Kandarpada": 20,
        "Mandapeshwar": 20,
        "Eksar": 10,
        "Borivali (West)": 10,
        "Pahadi Eksar": 10,
        "Kandivali (West)": 10,
        "Dahanukarwadi": 10,
        "Valnai": 10,
        "Malad (West)": 10,
        "Lower Malad": 20,
        "Pahadi Goregaon": 20,
        "Goregaon (West)": 20,
        "Oshiwara": 20,
        "Lower Oshiwara": 20,
        "DN Nagar": 20,
    },
    "Dahanukarwadi": {
        "Gundavali": 50,
        "Mogra": 40,
        "Jogeshwari (East)": 40,
        "Goregaon (East)": 40,
        "Aarey": 40,
        "Dindoshi": 40,
        "Kurar": 30,
        "Akurli": 30,
        "Poisar": 30,
        "Magathane": 30,
        "Devipada": 30,
        "Rashtriya Udyan": 30,
        "Ovripada": 20,
        "Dahisar (East)": 20,
        "Anand Nagar": 20,
        "Kandarpada": 20,
        "Mandapeshwar": 20,
        "Eksar": 20,
        "Borivali (West)": 10,
        "Pahadi Eksar": 10,
        "Kandivali (West)": 10,
        "Dahanukarwadi": 10,
        "Valnai": 10,
        "Malad (West)": 10,
        "Lower Malad": 10,
        "Pahadi Goregaon": 20,
        "Goregaon (West)": 20,
        "Oshiwara": 20,
        "Lower Oshiwara": 20,
        "DN Nagar": 20,
    },
    "Valnai": {
        "Gundavali": 50,
        "Mogra": 50,
        "Jogeshwari (East)": 40,
        "Goregaon (East)": 40,
        "Aarey": 40,
        "Dindoshi": 40,
        "Kurar": 40,
        "Akurli": 30,
        "Poisar": 30,
        "Magathane": 30,
        "Devipada": 30,
        "Rashtriya Udyan": 30,
        "Ovripada": 30,
        "Dahisar (East)": 20,
        "Anand Nagar": 20,
        "Kandarpada": 20,
        "Mandapeshwar": 20,
        "Eksar": 20,
        "Borivali (West)": 20,
        "Pahadi Eksar": 10,
        "Kandivali (West)": 10,
        "Dahanukarwadi": 10,
        "Valnai": 10,
        "Malad (West)": 10,
        "Lower Malad": 10,
        "Pahadi Goregaon": 10,
        "Goregaon (West)": 20,
        "Oshiwara": 20,
        "Lower Oshiwara": 20,
        "DN Nagar": 20,
    },
    "Malad (West)": {
        "Gundavali": 50,
        "Mogra": 50,
        "Jogeshwari (East)": 40,
        "Goregaon (East)": 40,
        "Aarey": 40,
        "Dindoshi": 40,
        "Kurar": 40,
        "Akurli": 30,
        "Poisar": 30,
        "Magathane": 30,
        "Devipada": 30,
        "Rashtriya Udyan": 30,
        "Ovripada": 30,
        "Dahisar (East)": 30,
        "Anand Nagar": 20,
        "Kandarpada": 20,
        "Mandapeshwar": 20,
        "Eksar": 20,
        "Borivali (West)": 20,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 10,
        "Dahanukarwadi": 10,
        "Valnai": 10,
        "Malad (West)": 10,
        "Lower Malad": 10,
        "Pahadi Goregaon": 10,
        "Goregaon (West)": 10,
        "Oshiwara": 20,
        "Lower Oshiwara": 20,
        "DN Nagar": 20,
    },
    "Lower Malad": {
        "Gundavali": 50,
        "Mogra": 50,
        "Jogeshwari (East)": 50,
        "Goregaon (East)": 40,
        "Aarey": 40,
        "Dindoshi": 40,
        "Kurar": 40,
        "Akurli": 40,
        "Poisar": 30,
        "Magathane": 30,
        "Devipada": 30,
        "Rashtriya Udyan": 30,
        "Ovripada": 30,
        "Dahisar (East)": 30,
        "Anand Nagar": 30,
        "Kandarpada": 20,
        "Mandapeshwar": 20,
        "Eksar": 20,
        "Borivali (West)": 20,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 10,
        "Valnai": 10,
        "Malad (West)": 10,
        "Lower Malad": 10,
        "Pahadi Goregaon": 10,
        "Goregaon (West)": 10,
        "Oshiwara": 10,
        "Lower Oshiwara": 10,
        "DN Nagar": 10,
    },
    "Pahadi Goregaon": {
        "Gundavali": 50,
        "Mogra": 50,
        "Jogeshwari (East)": 50,
        "Goregaon (East)": 50,
        "Aarey": 40,
        "Dindoshi": 40,
        "Kurar": 40,
        "Akurli": 40,
        "Poisar": 40,
        "Magathane": 30,
        "Devipada": 30,
        "Rashtriya Udyan": 30,
        "Ovripada": 30,
        "Dahisar (East)": 30,
        "Anand Nagar": 30,
        "Kandarpada": 30,
        "Mandapeshwar": 20,
        "Eksar": 20,
        "Borivali (West)": 20,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 20,
        "Valnai": 10,
        "Malad (West)": 10,
        "Lower Malad": 10,
        "Pahadi Goregaon": 10,
        "Goregaon (West)": 10,
        "Oshiwara": 10,
        "Lower Oshiwara": 10,
        "DN Nagar": 10,
    },
    "Goregaon (West)": {
        "Gundavali": 60,
        "Mogra": 50,
        "Jogeshwari (East)": 50,
        "Goregaon (East)": 50,
        "Aarey": 50,
        "Dindoshi": 40,
        "Kurar": 40,
        "Akurli": 40,
        "Poisar": 40,
        "Magathane": 40,
        "Devipada": 30,
        "Rashtriya Udyan": 30,
        "Ovripada": 30,
        "Dahisar (East)": 30,
        "Anand Nagar": 30,
        "Kandarpada": 30,
        "Mandapeshwar": 30,
        "Eksar": 20,
        "Borivali (West)": 20,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 20,
        "Valnai": 20,
        "Malad (West)": 10,
        "Lower Malad": 10,
        "Pahadi Goregaon": 10,
        "Goregaon (West)": 10,
        "Oshiwara": 10,
        "Lower Oshiwara": 10,
        "DN Nagar": 10,
    },
    "Oshiwara": {
        "Gundavali": 60,
        "Mogra": 60,
        "Jogeshwari (East)": 50,
        "Goregaon (East)": 50,
        "Aarey": 50,
        "Dindoshi": 50,
        "Kurar": 40,
        "Akurli": 40,
        "Poisar": 40,
        "Magathane": 40,
        "Devipada": 40,
        "Rashtriya Udyan": 30,
        "Ovripada": 30,
        "Dahisar (East)": 30,
        "Anand Nagar": 30,
        "Kandarpada": 30,
        "Mandapeshwar": 30,
        "Eksar": 30,
        "Borivali (West)": 20,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 20,
        "Valnai": 20,
        "Malad (West)": 20,
        "Lower Malad": 10,
        "Pahadi Goregaon": 10,
        "Goregaon (West)": 10,
        "Oshiwara": 10,
        "Lower Oshiwara": 10,
        "DN Nagar": 10,
    },
    "Lower Oshiwara": {
        "Gundavali": 60,
        "Mogra": 60,
        "Jogeshwari (East)": 50,
        "Goregaon (East)": 50,
        "Aarey": 50,
        "Dindoshi": 50,
        "Kurar": 50,
        "Akurli": 40,
        "Poisar": 40,
        "Magathane": 40,
        "Devipada": 40,
        "Rashtriya Udyan": 40,
        "Ovripada": 30,
        "Dahisar (East)": 30,
        "Anand Nagar": 30,
        "Kandarpada": 30,
        "Mandapeshwar": 30,
        "Eksar": 30,
        "Borivali (West)": 30,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 20,
        "Valnai": 20,
        "Malad (West)": 20,
        "Lower Malad": 10,
        "Pahadi Goregaon": 10,
        "Goregaon (West)": 10,
        "Oshiwara": 10,
        "Lower Oshiwara": 10,
        "DN Nagar": 10,
    },
    "DN Nagar": {
        "Gundavali": 60,
        "Mogra": 60,
        "Jogeshwari (East)": 60,
        "Goregaon (East)": 50,
        "Aarey": 50,
        "Dindoshi": 50,
        "Kurar": 50,
        "Akurli": 40,
        "Poisar": 40,
        "Magathane": 40,
        "Devipada": 40,
        "Rashtriya Udyan": 40,
        "Ovripada": 40,
        "Dahisar (East)": 30,
        "Anand Nagar": 30,
        "Kandarpada": 30,
        "Mandapeshwar": 30,
        "Eksar": 30,
        "Borivali (West)": 20,
        "Pahadi Eksar": 20,
        "Kandivali (West)": 20,
        "Dahanukarwadi": 20,
        "Valnai": 20,
        "Malad (West)": 20,
        "Lower Malad": 10,
        "Pahadi Goregaon": 10,
        "Goregaon (West)": 10,
        "Oshiwara": 10,
        "Lower Oshiwara": 10,
        "DN Nagar": 10,
    },
}

LINE_3_STATIONS = [
    "Acharya Atre Chowk",
    "Worli",
    "Siddhivinayak",
    "Dadar",
    "Shitala Devi Mandir",
    "Dharavi",
    "Bandra Kurla Complex",
    "Bandra Colony",
    "Santacruz Metro",
    "CSMIA T1",
    "Sahar Road",
    "CSMIA T2",
    "Marol Naka",
    "MIDC Andheri",
    "SEEPZ",
    "Aarey JVLR",
]

LINE_3_FARES = {
    "Acharya Atre Chowk": {
        "Acharya Atre Chowk": 10,
        "Worli": 10,
        "Siddhivinayak": 20,
        "Dadar": 20,
        "Shitala Devi Mandir": 30,
        "Dharavi": 40,
        "Bandra Kurla Complex": 40,
        "Bandra Colony": 40,
        "Santacruz Metro": 50,
        "CSMIA T1": 50,
        "Sahar Road": 50,
        "CSMIA T2": 60,
        "Marol Naka": 60,
        "MIDC Andheri": 60,
        "SEEPZ": 60,
        "Aarey JVLR": 60,
    },
    "Worli": {
        "Acharya Atre Chowk": 10,
        "Worli": 10,
        "Siddhivinayak": 10,
        "Dadar": 20,
        "Shitala Devi Mandir": 20,
        "Dharavi": 30,
        "Bandra Kurla Complex": 40,
        "Bandra Colony": 40,
        "Santacruz Metro": 40,
        "CSMIA T1": 50,
        "Sahar Road": 50,
        "CSMIA T2": 50,
        "Marol Naka": 50,
        "MIDC Andheri": 50,
        "SEEPZ": 60,
        "Aarey JVLR": 60,
    },
    "Siddhivinayak": {
        "Acharya Atre Chowk": 20,
        "Worli": 10,
        "Siddhivinayak": 10,
        "Dadar": 10,
        "Shitala Devi Mandir": 20,
        "Dharavi": 20,
        "Bandra Kurla Complex": 30,
        "Bandra Colony": 30,
        "Santacruz Metro": 40,
        "CSMIA T1": 40,
        "Sahar Road": 50,
        "CSMIA T2": 50,
        "Marol Naka": 50,
        "MIDC Andheri": 50,
        "SEEPZ": 50,
        "Aarey JVLR": 60,
    },
    "Dadar": {
        "Acharya Atre Chowk": 20,
        "Worli": 20,
        "Siddhivinayak": 10,
        "Dadar": 10,
        "Shitala Devi Mandir": 10,
        "Dharavi": 20,
        "Bandra Kurla Complex": 20,
        "Bandra Colony": 30,
        "Santacruz Metro": 30,
        "CSMIA T1": 40,
        "Sahar Road": 40,
        "CSMIA T2": 50,
        "Marol Naka": 50,
        "MIDC Andheri": 50,
        "SEEPZ": 50,
        "Aarey JVLR": 50,
    },
    "Shitala Devi Mandir": {
        "Acharya Atre Chowk": 30,
        "Worli": 20,
        "Siddhivinayak": 20,
        "Dadar": 10,
        "Shitala Devi Mandir": 10,
        "Dharavi": 10,
        "Bandra Kurla Complex": 20,
        "Bandra Colony": 20,
        "Santacruz Metro": 30,
        "CSMIA T1": 30,
        "Sahar Road": 40,
        "CSMIA T2": 40,
        "Marol Naka": 40,
        "MIDC Andheri": 40,
        "SEEPZ": 50,
        "Aarey JVLR": 50,
    },
    "Dharavi": {
        "Acharya Atre Chowk": 40,
        "Worli": 30,
        "Siddhivinayak": 20,
        "Dadar": 20,
        "Shitala Devi Mandir": 10,
        "Dharavi": 10,
        "Bandra Kurla Complex": 10,
        "Bandra Colony": 20,
        "Santacruz Metro": 20,
        "CSMIA T1": 20,
        "Sahar Road": 30,
        "CSMIA T2": 40,
        "Marol Naka": 40,
        "MIDC Andheri": 40,
        "SEEPZ": 40,
        "Aarey JVLR": 50,
    },
    "Bandra Kurla Complex": {
        "Acharya Atre Chowk": 40,
        "Worli": 40,
        "Siddhivinayak": 30,
        "Dadar": 20,
        "Shitala Devi Mandir": 20,
        "Dharavi": 10,
        "Bandra Kurla Complex": 10,
        "Bandra Colony": 10,
        "Santacruz Metro": 20,
        "CSMIA T1": 20,
        "Sahar Road": 30,
        "CSMIA T2": 30,
        "Marol Naka": 40,
        "MIDC Andheri": 40,
        "SEEPZ": 40,
        "Aarey JVLR": 40,
    },
    "Bandra Colony": {
        "Acharya Atre Chowk": 40,
        "Worli": 40,
        "Siddhivinayak": 30,
        "Dadar": 30,
        "Shitala Devi Mandir": 20,
        "Dharavi": 20,
        "Bandra Kurla Complex": 10,
        "Bandra Colony": 10,
        "Santacruz Metro": 10,
        "CSMIA T1": 20,
        "Sahar Road": 20,
        "CSMIA T2": 30,
        "Marol Naka": 30,
        "MIDC Andheri": 40,
        "SEEPZ": 40,
        "Aarey JVLR": 40,
    },
    "Santacruz Metro": {
        "Acharya Atre Chowk": 50,
        "Worli": 40,
        "Siddhivinayak": 40,
        "Dadar": 30,
        "Shitala Devi Mandir": 30,
        "Dharavi": 20,
        "Bandra Kurla Complex": 20,
        "Bandra Colony": 10,
        "Santacruz Metro": 10,
        "CSMIA T1": 10,
        "Sahar Road": 20,
        "CSMIA T2": 20,
        "Marol Naka": 20,
        "MIDC Andheri": 30,
        "SEEPZ": 30,
        "Aarey JVLR": 40,
    },
    "CSMIA T1": {
        "Acharya Atre Chowk": 50,
        "Worli": 50,
        "Siddhivinayak": 40,
        "Dadar": 40,
        "Shitala Devi Mandir": 30,
        "Dharavi": 20,
        "Bandra Kurla Complex": 20,
        "Bandra Colony": 20,
        "Santacruz Metro": 10,
        "CSMIA T1": 10,
        "Sahar Road": 10,
        "CSMIA T2": 20,
        "Marol Naka": 20,
        "MIDC Andheri": 30,
        "SEEPZ": 30,
        "Aarey JVLR": 30,
    },
    "Sahar Road": {
        "Acharya Atre Chowk": 50,
        "Worli": 50,
        "Siddhivinayak": 50,
        "Dadar": 40,
        "Shitala Devi Mandir": 40,
        "Dharavi": 30,
        "Bandra Kurla Complex": 30,
        "Bandra Colony": 20,
        "Santacruz Metro": 20,
        "CSMIA T1": 10,
        "Sahar Road": 10,
        "CSMIA T2": 10,
        "Marol Naka": 10,
        "MIDC Andheri": 20,
        "SEEPZ": 20,
        "Aarey JVLR": 30,
    },
    "CSMIA T2": {
        "Acharya Atre Chowk": 60,
        "Worli": 50,
        "Siddhivinayak": 50,
        "Dadar": 50,
        "Shitala Devi Mandir": 40,
        "Dharavi": 40,
        "Bandra Kurla Complex": 30,
        "Bandra Colony": 30,
        "Santacruz Metro": 20,
        "CSMIA T1": 20,
        "Sahar Road": 10,
        "CSMIA T2": 10,
        "Marol Naka": 10,
        "MIDC Andheri": 10,
        "SEEPZ": 20,
        "Aarey JVLR": 30,
    },
    "Marol Naka": {
        "Acharya Atre Chowk": 60,
        "Worli": 50,
        "Siddhivinayak": 50,
        "Dadar": 50,
        "Shitala Devi Mandir": 40,
        "Dharavi": 40,
        "Bandra Kurla Complex": 40,
        "Bandra Colony": 30,
        "Santacruz Metro": 20,
        "CSMIA T1": 20,
        "Sahar Road": 10,
        "CSMIA T2": 10,
        "Marol Naka": 10,
        "MIDC Andheri": 10,
        "SEEPZ": 10,
        "Aarey JVLR": 20,
    },
    "MIDC Andheri": {
        "Acharya Atre Chowk": 60,
        "Worli": 50,
        "Siddhivinayak": 50,
        "Dadar": 50,
        "Shitala Devi Mandir": 40,
        "Dharavi": 40,
        "Bandra Kurla Complex": 40,
        "Bandra Colony": 40,
        "Santacruz Metro": 30,
        "CSMIA T1": 30,
        "Sahar Road": 20,
        "CSMIA T2": 10,
        "Marol Naka": 10,
        "MIDC Andheri": 10,
        "SEEPZ": 10,
        "Aarey JVLR": 20,
    },
    "SEEPZ": {
        "Acharya Atre Chowk": 60,
        "Worli": 60,
        "Siddhivinayak": 50,
        "Dadar": 50,
        "Shitala Devi Mandir": 50,
        "Dharavi": 40,
        "Bandra Kurla Complex": 40,
        "Bandra Colony": 40,
        "Santacruz Metro": 30,
        "CSMIA T1": 30,
        "Sahar Road": 20,
        "CSMIA T2": 20,
        "Marol Naka": 10,
        "MIDC Andheri": 10,
        "SEEPZ": 10,
        "Aarey JVLR": 10,
    },
    "Aarey JVLR": {
        "Acharya Atre Chowk": 60,
        "Worli": 60,
        "Siddhivinayak": 60,
        "Dadar": 50,
        "Shitala Devi Mandir": 50,
        "Dharavi": 50,
        "Bandra Kurla Complex": 40,
        "Bandra Colony": 40,
        "Santacruz Metro": 40,
        "CSMIA T1": 30,
        "Sahar Road": 30,
        "CSMIA T2": 30,
        "Marol Naka": 20,
        "MIDC Andheri": 20,
        "SEEPZ": 10,
        "Aarey JVLR": 10,
    },
}

ALL_LINES_DATA: Dict[str, Tuple[List[str], Dict[str, Dict[str, int]]]] = {
    "Line 1 (Blue Line)": (LINE_1_STATIONS, LINE_1_FARES),
    "Line 2A & 7": (LINE_2A_7_STATIONS, LINE_2A_7_FARES),
    "Line 3 (Aqualine)": (LINE_3_STATIONS, LINE_3_FARES),
}

INTERCHANGES: List[Dict[str, str]] = [
    {
        "Line 1 (Blue Line)": "Marol Naka",
        "Line 3 (Aqualine)": "Marol Naka",
    },
    {
        "Line 1 (Blue Line)": "Western Express Highway",
        "Line 2A & 7": "Gundavali",
    },
    {
        "Line 1 (Blue Line)": "DN Nagar",
        "Line 2A & 7": "DN Nagar",
    },
]

_ALL_STATIONS_SET: Set[str] = set()
for stations, _ in ALL_LINES_DATA.values():
    _ALL_STATIONS_SET.update(stations)
_ALL_STATION_NAMES: List[str] = sorted(list(_ALL_STATIONS_SET))
MIN_FUZZY_SCORE = 85


_STATION_TO_LINE: Dict[str, Tuple[str, str]] = {}
for line_name, (stations, _) in ALL_LINES_DATA.items():
    for name in stations:
        _STATION_TO_LINE[name.lower()] = (line_name, name)


def _lookup_station(station: str) -> Tuple[str, str]:
    """
    Find the best matching canonical station name using fuzzy matching
    and return its associated line and canonical name from the _STATION_TO_LINE map.
    """
    query = station.strip()
    if not query:
        raise ValueError("Station name cannot be empty")

    match = process.extractOne(query, _ALL_STATION_NAMES)

    if match is None:
        raise ValueError(f"Station '{station}' not found on any supported metro line")

    best_match, score = match

    if score < MIN_FUZZY_SCORE:
        raise ValueError(
            f"Station '{station}' not found. Best guess '{best_match}' (score {score}) is below threshold {MIN_FUZZY_SCORE}"
        )

    key = best_match.lower()
    return _STATION_TO_LINE[key]


def _metro_same_line_fare(
    line_name: str,
    from_station: str,
    to_station: str,
) -> Dict[str, object]:
    fare_matrix = ALL_LINES_DATA[line_name][1]
    try:
        fare_rs = fare_matrix[from_station][to_station]
    except KeyError as exc:
        raise ValueError(
            f"Could not compute fare between {from_station} and {to_station} on {line_name}."
        ) from exc

    return {
        "mode": "metro",
        "total_fare_rs": fare_rs,
        "segments": [
            {
                "line": line_name,
                "from_station": from_station,
                "to_station": to_station,
                "fare_rs": fare_rs,
            }
        ],
    }


def _metro_interchange_fare(
    from_line: str,
    to_line: str,
    from_station: str,
    to_station: str,
) -> Dict[str, object]:
    best_route: Optional[Dict[str, object]] = None

    for interchange in INTERCHANGES:
        if from_line not in interchange or to_line not in interchange:
            continue

        from_interchange_station = interchange[from_line]
        to_interchange_station = interchange[to_line]

        first_segment = _metro_same_line_fare(
            from_line, from_station, from_interchange_station
        )
        second_segment = _metro_same_line_fare(
            to_line, to_interchange_station, to_station
        )

        total_fare = first_segment["total_fare_rs"] + second_segment["total_fare_rs"]

        route = {
            "mode": "metro",
            "total_fare_rs": total_fare,
            "segments": [
                *first_segment["segments"],
                {
                    "line": "interchange",
                    "from_station": from_interchange_station,
                    "to_station": to_interchange_station,
                    "fare_rs": 0,
                },
                *second_segment["segments"],
            ],
            "interchange_used": {
                "from_line": from_line,
                "to_line": to_line,
                "details": interchange,
            },
        }

        if best_route is None or route["total_fare_rs"] < best_route["total_fare_rs"]:
            best_route = route

    if best_route is None:
        raise ValueError(
            "No supported interchange found between the selected lines. "
            "Supported interchanges: Marol Naka (Line 1 ↔ Line 3), Western Express Highway ↔ Gundavali (Line 1 ↔ Line 2A & 7), DN Nagar (Line 1 ↔ Line 2A & 7)."
        )

    return best_route


def _metro_fare(from_station_raw: str, to_station_raw: str) -> Dict[str, object]:
    from_line, from_station = _lookup_station(from_station_raw)
    to_line, to_station = _lookup_station(to_station_raw)

    if from_line == to_line:
        return _metro_same_line_fare(from_line, from_station, to_station)

    return _metro_interchange_fare(from_line, to_line, from_station, to_station)


_INTERCHANGE_DESCRIPTIONS = [
    "Marol Naka (Line 1 ↔ Line 3)",
    "Western Express Highway/Gundavali (Line 1 ↔ Line 2A & 7)",
    "DN Nagar (Line 1 ↔ Line 2A & 7)",
]


METRO_DESCRIPTION = (
    "Metro coverage: Line 1 (Blue Line) stations -> "
    + ", ".join(LINE_1_STATIONS)
    + ". Line 2A & 7 stations -> "
    + ", ".join(LINE_2A_7_STATIONS)
    + ". Line 3 (Aqualine) stations -> "
    + ", ".join(LINE_3_STATIONS)
    + ". Interchanges -> "
    + "; ".join(_INTERCHANGE_DESCRIPTIONS)
    + ". Station names support fuzzy matching."
)


@mcp.tool(name="fare_lookup")
async def fare_lookup(
    mode: FareMode = "road",
    vehicle_type: Optional[str] = None,
    distance_km: Optional[float] = None,
    fare_variant: FareVariant = "revised",
    time_period: TimePeriod = "normal",
    from_station: Optional[str] = None,
    to_station: Optional[str] = None,
) -> Dict[str, object]:
    """
    Retrieve official fares for Mumbai road transport or the supported metro network.

    **TOOL SIGNATURE:**
    ```python
    fare_lookup(
        mode: Literal["road", "metro"] = "road",
        vehicle_type: Optional[str] = None,  # Required for mode="road"
        distance_km: Optional[float] = None,  # Required for mode="road", must be > 0
        fare_variant: Literal["old", "revised"] = "revised",  # Road only
        time_period: Literal["normal", "midnight"] = "normal",  # Road only
        from_station: Optional[str] = None,  # Required for mode="metro"
        to_station: Optional[str] = None,  # Required for mode="metro"
    ) -> Dict[str, Any]
    ```

    **PARAMETERS:**
    - mode (str): Transport mode - "road" for auto/taxi, "metro" for suburban metro
    - vehicle_type (str): Vehicle type for road fares (e.g., "auto-rickshaw", "black-yellow taxi")
    - distance_km (float): Distance in kilometers for road fares (must be positive)
    - fare_variant (str): Tariff version - "old" or "revised" (road only)
    - time_period (str): Time band - "normal" or "midnight" (road only)
    - from_station (str): Origin metro station (supports fuzzy matching)
    - to_station (str): Destination metro station (supports fuzzy matching)

    **RETURNS:**
    Dict[str, Any] with structure depending on mode:

    For mode="road":
    {
        "mode": "road",
        "vehicle_type": str,
        "distance_km": float,
        "fare_variant": str,
        "time_period": str,
        "fare_rs": float,
        "full_record": {
            "old_normal": float,
            "revised_normal": float,
            "old_midnight": float,
            "revised_midnight": float
        }
    }

    For mode="metro":
    {
        "mode": "metro",
        "total_fare_rs": int,
        "from_station_raw_input": str,
        "to_station_raw_input": str,
        "segments": [
            {
                "line": str,
                "from_station": str,
                "to_station": str,
                "fare_rs": int
            }
        ],
        "interchange_used": Optional[Dict]  # If interchange required
    }

    **USAGE EXAMPLES:**

    Example 1 - Road fare lookup:
    ```python
    result = await fare_lookup(
        mode="road",
        vehicle_type="auto-rickshaw",
        distance_km=5.5,
        fare_variant="revised",
        time_period="normal"
    )
    # Returns: {"mode": "road", "fare_rs": 45.0, ...}
    ```

    Example 2 - Metro same-line fare:
    ```python
    result = await fare_lookup(
        mode="metro",
        from_station="Versova",
        to_station="Ghatkopar"
    )
    # Returns: {"mode": "metro", "total_fare_rs": 110, ...}
    ```

    Example 3 - Metro with fuzzy matching:
    ```python
    result = await fare_lookup(
        mode="metro",
        from_station="versuva",  # Fuzzy matched to "Versova"
        to_station="ghatkoper"   # Fuzzy matched to "Ghatkopar"
    )
    ```

    Example 4 - Metro interchange route:
    ```python
    result = await fare_lookup(
        mode="metro",
        from_station="Versova",  # Line 1
        to_station="Worli"       # Line 3
    )
    # Returns interchange details via Marol Naka
    ```

    **METRO COVERAGE:**
    - Line 1 (Blue Line): Versova to Ghatkopar (12 stations)
    - Line 2A & 7: Gundavali to DN Nagar (30 stations)
    - Line 3 (Aqualine): Acharya Atre Chowk to Aarey JVLR (16 stations)
    - Interchanges: Marol Naka (Line 1↔3), Western Express Highway/Gundavali (Line 1↔2A&7), DN Nagar (Line 1↔2A&7)

    **ERROR CONDITIONS:**
    - ValueError: Invalid mode, missing required parameters, unsupported vehicle type/distance
    - ValueError: Station not found or fuzzy match score too low (< 85)
    - ValueError: No interchange available between requested lines
    """
    if mode == "road":
        if not vehicle_type or not distance_km:
            raise ValueError(
                "vehicle_type and distance_km are required for mode='road'"
            )
        if distance_km <= 0:
            raise ValueError("distance_km must be positive")

        fare_table = _load_fare_table()
        vehicle_match = process.extractOne(vehicle_type, fare_table.keys())
        if not vehicle_match or vehicle_match[1] < 85:
            raise ValueError(
                f"Vehicle type '{vehicle_type}' not found. Available types: {list(fare_table.keys())}"
            )

        matched_vehicle_type = vehicle_match[0]
        vehicle_fares = fare_table[matched_vehicle_type]

        available_distances = sorted(vehicle_fares.keys())
        if distance_km < available_distances[0]:
            raise ValueError(
                f"Distance {distance_km}km is below the minimum of {available_distances[0]}km for {matched_vehicle_type}"
            )

        fare_distance = max(d for d in available_distances if d <= distance_km)

        record = vehicle_fares[fare_distance]
        fare = _select_fare(record, fare_variant, time_period)

        return {
            "mode": "road",
            "vehicle_type": record.vehicle_type,
            "distance_km": distance_km,
            "fare_variant": fare_variant,
            "time_period": time_period,
            "fare_rs": fare,
            "full_record": {
                "old_normal": record.old_normal,
                "revised_normal": record.revised_normal,
                "old_midnight": record.old_midnight,
                "revised_midnight": record.revised_midnight,
            },
        }

    if mode == "metro":
        if not from_station or not to_station:
            raise ValueError(
                "from_station and to_station are required for mode='metro'"
            )
        result = _metro_fare(from_station, to_station)
        result["from_station_raw_input"] = from_station
        result["to_station_raw_input"] = to_station
        return result

    raise ValueError(f"Invalid mode '{mode}'. Must be 'road' or 'metro'.")
