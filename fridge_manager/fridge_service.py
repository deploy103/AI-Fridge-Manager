from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Literal


MAX_FOOD_NAME_LENGTH = 60
JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


class AIResponseError(RuntimeError):
    pass


@dataclass(frozen=True)
class StorageDecision:
    food_name: str
    need_fridge: bool
    reason: str


@dataclass(frozen=True)
class AddFoodResult:
    status: Literal["added", "rejected", "duplicate"]
    item_name: str
    reason: str


@dataclass(frozen=True)
class FridgeItem:
    name: str
    reason: str


@dataclass(frozen=True)
class MenuRecommendation:
    menu: str
    reason: str


def normalize_food_name(food_name: str) -> str:
    normalized = unicodedata.normalize("NFC", food_name or "")
    return re.sub(r"\s+", " ", normalized).strip()


def validate_food_name(food_name: str) -> str | None:
    normalized = normalize_food_name(food_name)

    if not normalized:
        return "식품 이름을 입력해 주세요."

    if len(normalized) > MAX_FOOD_NAME_LENGTH:
        return f"식품 이름은 {MAX_FOOD_NAME_LENGTH}자 이하로 입력해 주세요."

    if not any(char.isalnum() for char in normalized):
        return "식품 이름에는 글자나 숫자가 포함되어야 합니다."

    if any(unicodedata.category(char).startswith("C") for char in normalized):
        return "제어 문자가 포함된 입력은 사용할 수 없습니다."

    return None


class FridgeManager:
    def __init__(self):
        self._items: list[FridgeItem] = []

    @property
    def items(self) -> tuple[FridgeItem, ...]:
        return tuple(self._items)

    def add_decision(self, decision: StorageDecision) -> AddFoodResult:
        existing_item = self.find_item(decision.food_name)
        if existing_item is not None:
            return AddFoodResult(
                status="duplicate",
                item_name=existing_item.name,
                reason=f"이미 냉장고 목록에 있습니다. 보관 판단 사유: {decision.reason}",
            )

        if decision.need_fridge:
            item = FridgeItem(name=decision.food_name, reason=decision.reason)
            self._items.append(item)
            return AddFoodResult(
                status="added",
                item_name=item.name,
                reason=item.reason,
            )

        return AddFoodResult(
            status="rejected",
            item_name=decision.food_name,
            reason=decision.reason,
        )

    def find_item(self, food_name: str) -> FridgeItem | None:
        target_key = normalize_food_name(food_name).casefold()

        for item in self._items:
            item_key = normalize_food_name(item.name).casefold()
            if item_key == target_key:
                return item

        return None


class FridgeAI:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model

    def check_storage(self, food_name: str) -> StorageDecision:
        normalized_name = normalize_food_name(food_name)
        payload = self._request_json(
            f"""
당신은 식품 보관을 도와주는 전문가입니다.
사용자가 지금 식품을 보관하려는 일반적인 가정 상황을 기준으로 판단하세요.
포장 상태가 애매하면 개봉 후 보관 또는 바로 보관하는 상황을 우선 가정하세요.

식품명: {normalized_name}

반드시 아래 JSON 객체 하나만 반환하세요.
{{
  "need_fridge": true,
  "reason": "한국어로 짧고 구체적인 보관 사유"
}}

규칙:
- 냉장 보관이 필요하면 need_fridge를 true로 작성하세요.
- 실온 보관이 일반적이면 need_fridge를 false로 작성하세요.
- reason은 한국어로 작성하고 1~2문장 안에서 끝내세요.
""".strip()
        )

        need_fridge = payload.get("need_fridge")
        reason = str(payload.get("reason", "")).strip()

        if not isinstance(need_fridge, bool):
            raise AIResponseError("보관 판정 결과에 need_fridge 불리언 값이 없습니다.")

        if not reason:
            raise AIResponseError("보관 판정 결과에 reason이 없습니다.")

        return StorageDecision(
            food_name=normalized_name,
            need_fridge=need_fridge,
            reason=reason,
        )

    def recommend_menu(self, items: Iterable[FridgeItem]) -> MenuRecommendation:
        ingredient_names = [item.name for item in items]
        if not ingredient_names:
            raise AIResponseError("추천에 사용할 식품이 없습니다.")

        ingredient_text = ", ".join(ingredient_names)
        payload = self._request_json(
            f"""
당신은 냉장고 재료로 현실적인 메뉴를 추천하는 요리 도우미입니다.
사용 가능한 재료로 가장 무난하고 만들기 쉬운 메뉴 하나를 추천하세요.
부족한 재료가 있더라도 소금, 후추, 물, 식용유, 기본 양념 정도만 최소한으로 가정할 수 있습니다.

사용 가능한 재료: {ingredient_text}

반드시 아래 JSON 객체 하나만 반환하세요.
{{
  "menu": "추천 메뉴 이름",
  "reason": "한국어로 구체적인 추천 이유"
}}

규칙:
- menu와 reason은 모두 한국어로 작성하세요.
- reason에는 어떤 재료 조합이 잘 맞는지, 왜 현실적인 선택인지 포함하세요.
- 너무 거창한 요리보다 실제로 만들 가능성이 높은 메뉴를 우선하세요.
""".strip()
        )

        menu = normalize_food_name(str(payload.get("menu", "")))
        reason = str(payload.get("reason", "")).strip()

        if not menu:
            raise AIResponseError("추천 결과에 menu가 없습니다.")

        if not reason:
            raise AIResponseError("추천 결과에 reason이 없습니다.")

        return MenuRecommendation(menu=menu, reason=reason)

    def _request_json(self, prompt: str) -> dict:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        output_text = (response.output_text or "").strip()
        return self._parse_json(output_text)

    def _parse_json(self, output_text: str) -> dict:
        if not output_text:
            raise AIResponseError("AI 응답이 비어 있습니다.")

        try:
            payload = json.loads(output_text)
        except json.JSONDecodeError as error:
            match = JSON_OBJECT_PATTERN.search(output_text)
            if match is None:
                raise AIResponseError("AI가 JSON 형식으로 응답하지 않았습니다.") from error

            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError as nested_error:
                raise AIResponseError("AI JSON 응답을 해석할 수 없습니다.") from nested_error

        if not isinstance(payload, dict):
            raise AIResponseError("AI 응답 JSON이 객체 형식이 아닙니다.")

        return payload
