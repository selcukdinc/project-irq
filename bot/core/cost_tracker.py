"""
bot/core/cost_tracker.py — Claude Code maliyet takip sistemi

Bu modül Claude Code API çağrılarının maliyetini takip eder.
Claude CLI'nın --verbose ve --max-budget-usd flag'lerini kullanır.
"""

import json
import os
import re
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CostEntry:
    """Tek bir Claude Code çalıştırmasının maliyet bilgisi"""
    timestamp: datetime
    project: str
    prompt: str
    model: str
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0


class CostTracker:
    """Claude Code maliyet takibi ve limit kontrolü"""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.cost_file = config_dir / "costs.json"
        self.config_file = config_dir / "config.json"

        # Maliyet hesaplaması için model bazlı ücretler (USD per million tokens)
        # Anthropic API pricing (Mart 2026 fiyatları)
        self.model_costs = {
            "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
            "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
            "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
            # Diğer modeller için varsayılan (Sonnet fiyatı)
            "default": {"input": 3.0, "output": 15.0}
        }

    def get_daily_limit(self) -> float:
        """Günlük maliyet limitini al"""
        try:
            if self.config_file.exists():
                with open(self.config_file) as f:
                    config = json.load(f)
                    return float(config.get("daily_cost_limit_usd", 5.0))
        except Exception as e:
            logger.warning(f"Config okuma hatası: {e}")

        # Varsayılan limit
        return 5.0

    def set_daily_limit(self, limit_usd: float):
        """Günlük maliyet limitini ayarla"""
        try:
            config = {}
            if self.config_file.exists():
                with open(self.config_file) as f:
                    config = json.load(f)

            config["daily_cost_limit_usd"] = limit_usd

            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Günlük maliyet limiti {limit_usd} USD olarak ayarlandı")

        except Exception as e:
            logger.error(f"Maliyet limiti ayarlama hatası: {e}")
            raise

    def parse_claude_output(self, stdout: str, stderr: str, model: str) -> Tuple[int, int, float]:
        """
        Claude Code çıktısından token ve maliyet bilgisini parse et

        Returns:
            (input_tokens, output_tokens, estimated_cost_usd)
        """
        input_tokens = 0
        output_tokens = 0

        # Claude CLI'nın verbose çıktısından token bilgisini parse et
        # Pattern örnekleri:
        # "Input tokens: 1234"
        # "Output tokens: 567"
        # "Total cost: $0.045"

        combined_output = stdout + stderr

        # Token sayılarını parse et
        input_match = re.search(r'input.*?tokens?.*?:?\s*(\d+)', combined_output, re.IGNORECASE)
        if input_match:
            input_tokens = int(input_match.group(1))

        output_match = re.search(r'output.*?tokens?.*?:?\s*(\d+)', combined_output, re.IGNORECASE)
        if output_match:
            output_tokens = int(output_match.group(1))

        # Maliyet parse et (varsa)
        cost_match = re.search(r'cost.*?\$?(\d+\.?\d*)', combined_output, re.IGNORECASE)
        actual_cost = 0.0
        if cost_match:
            actual_cost = float(cost_match.group(1))

        # Eğer Claude çıktısında maliyet yoksa, token bazlı hesaplama yap
        estimated_cost = self._estimate_cost(model, input_tokens, output_tokens)

        # Gerçek maliyet varsa onu kullan, yoksa tahmin edilen maliyeti kullan
        final_cost = actual_cost if actual_cost > 0 else estimated_cost

        logger.debug(f"Token parse: input={input_tokens}, output={output_tokens}, cost=${final_cost:.4f}")
        return input_tokens, output_tokens, final_cost

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Model ve token sayısına göre tahmini maliyet hesapla"""
        model_cost = self.model_costs.get(model, self.model_costs["default"])

        input_cost = (input_tokens / 1_000_000) * model_cost["input"]
        output_cost = (output_tokens / 1_000_000) * model_cost["output"]

        return input_cost + output_cost

    def record_usage(self, project: str, prompt: str, model: str,
                    stdout: str, stderr: str, duration_seconds: float):
        """Claude Code kullanımını kaydet"""

        # Token ve maliyet bilgisini parse et
        input_tokens, output_tokens, cost_usd = self.parse_claude_output(stdout, stderr, model)

        entry = CostEntry(
            timestamp=datetime.now(),
            project=project,
            prompt=prompt[:100],  # Prompt'u kısalt
            model=model,
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost_usd=cost_usd,
            duration_seconds=duration_seconds
        )

        self._save_cost_entry(entry)

        # Günlük limite yakın mı kontrol et
        daily_spent = self.get_daily_cost()
        daily_limit = self.get_daily_limit()

        if daily_spent >= daily_limit * 0.8:  # %80'ine ulaştı
            logger.warning(f"Günlük maliyet limitine yaklaşıldı: ${daily_spent:.2f} / ${daily_limit:.2f}")

        return entry

    def _save_cost_entry(self, entry: CostEntry):
        """Maliyet kaydını dosyaya yaz"""
        try:
            costs = []
            if self.cost_file.exists():
                with open(self.cost_file) as f:
                    costs = json.load(f)

            cost_dict = {
                "timestamp": entry.timestamp.isoformat(),
                "project": entry.project,
                "prompt": entry.prompt,
                "model": entry.model,
                "tokens_input": entry.tokens_input,
                "tokens_output": entry.tokens_output,
                "cost_usd": entry.cost_usd,
                "duration_seconds": entry.duration_seconds
            }

            costs.append(cost_dict)

            # Son 1000 kaydı tut (disk alanı yönetimi)
            if len(costs) > 1000:
                costs = costs[-1000:]

            with open(self.cost_file, 'w') as f:
                json.dump(costs, f, indent=2)

        except Exception as e:
            logger.error(f"Maliyet kaydı yazma hatası: {e}")

    def get_daily_cost(self, target_date: Optional[date] = None) -> float:
        """Belirli bir günün toplam maliyetini al"""
        if target_date is None:
            target_date = date.today()

        try:
            if not self.cost_file.exists():
                return 0.0

            with open(self.cost_file) as f:
                costs = json.load(f)

            daily_total = 0.0
            for cost in costs:
                entry_date = datetime.fromisoformat(cost["timestamp"]).date()
                if entry_date == target_date:
                    daily_total += cost["cost_usd"]

            return daily_total

        except Exception as e:
            logger.error(f"Günlük maliyet hesaplama hatası: {e}")
            return 0.0

    def get_cost_summary(self, days: int = 7) -> Dict:
        """Son N günün maliyet özetini al"""
        try:
            if not self.cost_file.exists():
                return {"total_cost": 0.0, "daily_costs": [], "usage_by_model": {}}

            with open(self.cost_file) as f:
                costs = json.load(f)

            cutoff_date = date.today() - datetime.timedelta(days=days)

            total_cost = 0.0
            daily_costs = {}
            model_usage = {}

            for cost in costs:
                entry_date = datetime.fromisoformat(cost["timestamp"]).date()
                if entry_date >= cutoff_date:

                    # Toplam maliyet
                    total_cost += cost["cost_usd"]

                    # Günlük breakdown
                    date_str = entry_date.isoformat()
                    daily_costs[date_str] = daily_costs.get(date_str, 0.0) + cost["cost_usd"]

                    # Model bazlı kullanım
                    model = cost["model"]
                    if model not in model_usage:
                        model_usage[model] = {"count": 0, "cost": 0.0, "tokens": 0}

                    model_usage[model]["count"] += 1
                    model_usage[model]["cost"] += cost["cost_usd"]
                    model_usage[model]["tokens"] += cost["tokens_input"] + cost["tokens_output"]

            return {
                "total_cost": total_cost,
                "daily_costs": daily_costs,
                "usage_by_model": model_usage,
                "daily_limit": self.get_daily_limit()
            }

        except Exception as e:
            logger.error(f"Maliyet özeti hesaplama hatası: {e}")
            return {"total_cost": 0.0, "daily_costs": [], "usage_by_model": {}}

    def check_daily_limit_exceeded(self) -> bool:
        """Günlük limit aşıldı mı kontrol et"""
        daily_spent = self.get_daily_cost()
        daily_limit = self.get_daily_limit()
        return daily_spent >= daily_limit

    def get_remaining_budget(self) -> float:
        """Kalan günlük bütçeyi al"""
        daily_spent = self.get_daily_cost()
        daily_limit = self.get_daily_limit()
        return max(0.0, daily_limit - daily_spent)