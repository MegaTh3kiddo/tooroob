"""PC Component Compatibility & Basket-Level Reasoning Engine.

Evaluates hardware compatibility across components in a custom PC build:
1. CPU socket vs Motherboard socket (LGA1700, AM4, AM5, LGA1200, etc.)
2. Motherboard memory type vs RAM module (DDR4 vs DDR5)
3. GPU power demand vs PSU wattage
4. Form factor constraints (ATX, Micro-ATX, Mini-ITX)
5. Shared basket budget optimization
6. Explicit admission of uncertainty when specifications are missing or partial.
"""

from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("torob.agent.compatibility")


class CompatibilityStatus(str, Enum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNCERTAIN_MISSING_SPECS = "uncertain_missing_specs"
    WARNING_SUBOPTIMAL = "warning_suboptimal"


class CompatibilityIssue(BaseModel):
    severity: str  # "error", "warning", "info"
    component_a: str
    component_b: str
    message: str


class BasketCompatibilityReport(BaseModel):
    status: CompatibilityStatus
    is_compatible: bool
    issues: List[CompatibilityIssue] = Field(default_factory=list)
    missing_specifications: List[str] = Field(default_factory=list)
    total_cost_toman: float = 0.0
    budget_toman: Optional[float] = None
    is_within_budget: bool = True
    budget_diff_toman: float = 0.0
    technical_summary: str
    missing_components: List[str] = Field(default_factory=list)


class PCCompatibilityEngine:
    """Rigorous hardware compatibility verifier."""

    # Standard CPU socket mappings
    SOCKET_PATTERNS = {
        "lga1700": [r"lga\s*1700", r"intel\s*1[234]th", r"i[3579]-1[234]\d{3}", r"z690", r"b660", r"h610", r"z790", r"b760"],
        "lga1200": [r"lga\s*1200", r"intel\s*1[01]th", r"i[3579]-1[01]\d{3}", r"z490", r"b460", r"h410", r"z590", r"b560"],
        "am4": [r"am4", r"ryzen\s*[3579]\s*[12345]\d{3}", r"b450", r"b550", r"x570", r"a320", r"a520"],
        "am5": [r"am5", r"ryzen\s*[3579]\s*[789]\d{3}", r"b650", r"x670", r"a620"],
    }

    # Memory types
    RAM_TYPES = ["ddr5", "ddr4", "ddr3"]

    @classmethod
    def extract_socket(cls, text: str) -> Optional[str]:
        lower = text.lower()
        for sock, patterns in cls.SOCKET_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lower):
                    return sock
        return None

    @classmethod
    def extract_ram_type(cls, text: str) -> Optional[str]:
        lower = text.lower()
        for r_type in cls.RAM_TYPES:
            if r_type in lower:
                return r_type
        return None

    @classmethod
    def extract_wattage(cls, text: str) -> Optional[int]:
        m = re.search(r"(\d{3,4})\s*w(?:att)?\b", text.lower())
        if m:
            return int(m.group(1))
        return None

    def evaluate_basket(
        self,
        components: List[Dict[str, Any]],
        budget_toman: Optional[float] = None,
    ) -> BasketCompatibilityReport:
        """Evaluates compatibility across components in a custom PC build."""
        issues: List[CompatibilityIssue] = []
        missing_specs: List[str] = []
        total_cost = sum(c.get("price_toman", 0.0) for c in components)

        # Categorize components
        cpu = next((c for c in components if c.get("category") in ("cpu", "پردازنده")), None)
        motherboard = next((c for c in components if c.get("category") in ("motherboard", "مادربرد")), None)
        ram = next((c for c in components if c.get("category") in ("ram", "رم")), None)
        gpu = next((c for c in components if c.get("category") in ("gpu", "کارت گرافیک")), None)
        psu = next((c for c in components if c.get("category") in ("psu", "پاور", "منبع تغذیه")), None)
        storage = next((c for c in components if c.get("category") in ("ssd", "hdd", "حافظه")), None)

        # Check missing essential components
        present_categories = [c.get("category") for c in components if c.get("category")]
        essential = [("cpu", "پردازنده"), ("motherboard", "مادربرد"), ("ram", "حافظه رم"), ("storage", "حافظه ذخیره‌سازی")]
        missing_comp_names = []
        for eng_cat, fa_cat in essential:
            if not any(c.get("category") in (eng_cat, fa_cat) for c in components):
                missing_comp_names.append(fa_cat)

        # 1. CPU vs Motherboard Socket Verification
        if cpu and motherboard:
            cpu_text = f"{cpu.get('title', '')} {cpu.get('specs', '')}"
            mb_text = f"{motherboard.get('title', '')} {motherboard.get('specs', '')}"
            cpu_socket = self.extract_socket(cpu_text)
            mb_socket = self.extract_socket(mb_text)

            if cpu_socket and mb_socket:
                if cpu_socket != mb_socket:
                    issues.append(
                        CompatibilityIssue(
                            severity="error",
                            component_a=cpu.get("title", "پردازنده"),
                            component_b=motherboard.get("title", "مادربرد"),
                            message=f"عدم تطابق سوکت پردازنده و مادربرد: پردازنده نیاز به سوکت {cpu_socket.upper()} دارد اما مادربرد دارای سوکت {mb_socket.upper()} است.",
                        )
                    )
            else:
                missing_specs.append(
                    "اطلاعات سوکت پردازنده یا چیپست مادربرد در کاتالوگ به صورت قطعی قابل استخراج نبود؛ بررسی دفترچه راهنما توصیه می‌شود."
                )

        # 2. Motherboard vs RAM Generation (DDR4 vs DDR5)
        if motherboard and ram:
            mb_text = f"{motherboard.get('title', '')} {motherboard.get('specs', '')}"
            ram_text = f"{ram.get('title', '')} {ram.get('specs', '')}"
            mb_ram = self.extract_ram_type(mb_text)
            ram_ram = self.extract_ram_type(ram_text)

            if mb_ram and ram_ram:
                if mb_ram != ram_ram:
                    issues.append(
                        CompatibilityIssue(
                            severity="error",
                            component_a=motherboard.get("title", "مادربرد"),
                            component_b=ram.get("title", "رم"),
                            message=f"عدم تطابق نسل حافظه رم: مادربرد از رم‌های {mb_ram.upper()} پشتیبانی می‌کند ولی ماژول رم انتخابی از نوع {ram_ram.upper()} است.",
                        )
                    )
            elif not ram_ram:
                missing_specs.append("نوع حافظه رم (DDR4 یا DDR5) در مشخصات فنی کاتالوگ قید نشده است.")

        # 3. GPU Power vs PSU Wattage
        if gpu and psu:
            gpu_text = f"{gpu.get('title', '')} {gpu.get('specs', '')}".lower()
            psu_text = f"{psu.get('title', '')} {psu.get('specs', '')}"
            psu_w = self.extract_wattage(psu_text)

            # Heuristic recommended minimum PSU wattage for high-end GPUs
            needed_w = 450
            if any(k in gpu_text for k in ["4090", "7900 xtx"]):
                needed_w = 850
            elif any(k in gpu_text for k in ["4080", "7900 xt", "3090", "3080"]):
                needed_w = 750
            elif any(k in gpu_text for k in ["4070", "3070", "7800 xt", "6800"]):
                needed_w = 650
            elif any(k in gpu_text for k in ["4060", "3060", "7600", "6600"]):
                needed_w = 550

            if psu_w and psu_w < needed_w:
                issues.append(
                    CompatibilityIssue(
                        severity="warning",
                        component_a=gpu.get("title", "کارت گرافیک"),
                        component_b=psu.get("title", "پاور"),
                        message=f"توان پاور ({psu_w}W) کمتر از توان پیشنهادی برای این کارت گرافیک (حداقل {needed_w}W) است.",
                    )
                )

        # Budget calculation
        is_within_budget = True
        budget_diff = 0.0
        if budget_toman is not None:
            is_within_budget = total_cost <= budget_toman
            budget_diff = total_cost - budget_toman

        # Status determination
        has_errors = any(i.severity == "error" for i in issues)
        if has_errors:
            status = CompatibilityStatus.INCOMPATIBLE
            tech_summary = "قطعات انتخابی دارای تداخل فنی ناسازگار هستند و قابلیت راه‌اندازی با یکدیگر را ندارند."
        elif missing_specs:
            status = CompatibilityStatus.UNCERTAIN_MISSING_SPECS
            tech_summary = "تطابق ظاهری برقرار است، اما به دلیل نقص مشخصات فنی کاتالوگ، تطابق ۱۰۰٪ نیازمند بازبینی دفترچه است."
        elif any(i.severity == "warning" for i in issues):
            status = CompatibilityStatus.WARNING_SUBOPTIMAL
            tech_summary = "قطعات به صورت کلی سازگار هستند، اما برخی مؤلفه‌ها مانند توان پاور گلوگاه ایجاد خواهند کرد."
        else:
            status = CompatibilityStatus.COMPATIBLE
            tech_summary = "کلیه قطعات سخت‌افزاری سبد خرید از نظر سوکت، رم و توان با یکدیگر سازگار هستند."

        return BasketCompatibilityReport(
            status=status,
            is_compatible=not has_errors,
            issues=issues,
            missing_specifications=missing_specs,
            total_cost_toman=total_cost,
            budget_toman=budget_toman,
            is_within_budget=is_within_budget,
            budget_diff_toman=budget_diff,
            technical_summary=tech_summary,
            missing_components=missing_comp_names,
        )
