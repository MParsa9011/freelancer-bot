import re
from dataclasses import dataclass, field


@dataclass
class Project:
    project_id: str
    title: str
    url: str
    budget_min: float | None
    budget_max: float | None
    bid_count: int
    avg_bid: float | None
    description: str
    skills: list[str] = field(default_factory=list)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_budget(text: str) -> tuple[float | None, float | None]:
    text = text.replace(",", "").replace("\xa0", " ")
    nums = re.findall(r"[\d]+(?:\.\d+)?", text)
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    if len(nums) == 1:
        return float(nums[0]), float(nums[0])
    return None, None


def parse_number(text: str) -> int:
    nums = re.findall(r"\d+", text.replace(",", ""))
    return int(nums[0]) if nums else 0


def parse_float(text: str) -> float | None:
    nums = re.findall(r"[\d]+(?:\.\d+)?", text.replace(",", ""))
    return float(nums[0]) if nums else None
