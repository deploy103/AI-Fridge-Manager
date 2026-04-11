import os
import sys
from ctypes import windll
from dataclasses import dataclass

from openai import OpenAI

from fridge_manager.fridge_service import (
    AIResponseError,
    FridgeAI,
    FridgeManager,
    validate_food_name,
)
from fridge_manager.settings import ConfigError, load_settings


EMPTY_INVENTORY_SUMMARY = "냉장고에 식품이 없습니다. 한글 이름으로 바로 추가할 수 있습니다."
DEFAULT_DECISION_TITLE = "아직 판정한 식품이 없습니다."
DEFAULT_DECISION_REASON = "식품을 추가하면 냉장 여부와 사유가 여기에 표시됩니다."
DEFAULT_RECOMMEND_TITLE = "추천 메뉴가 아직 없습니다."
DEFAULT_RECOMMEND_REASON = (
    "냉장고에 재료를 추가한 뒤 버튼을 누르면 메뉴와 추천 이유를 보여줍니다."
)


@dataclass
class CLIState:
    inventory_summary: str
    decision_label: str
    decision_title: str
    decision_reason: str
    recommend_title: str
    recommend_reason: str
    status: str


def configure_console_encoding():
    if os.name == "nt":
        try:
            windll.kernel32.SetConsoleCP(65001)
            windll.kernel32.SetConsoleOutputCP(65001)
        except OSError:
            pass

    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                continue


def prompt_input(message):
    try:
        return input(message)
    except (EOFError, KeyboardInterrupt):
        print("\n프로그램을 종료합니다.")
        return None


def clear_screen():
    if not sys.stdout.isatty():
        return

    os.system("cls" if os.name == "nt" else "clear")


def create_initial_state(model):
    return CLIState(
        inventory_summary=EMPTY_INVENTORY_SUMMARY,
        decision_label="대기 중",
        decision_title=DEFAULT_DECISION_TITLE,
        decision_reason=DEFAULT_DECISION_REASON,
        recommend_title=DEFAULT_RECOMMEND_TITLE,
        recommend_reason=DEFAULT_RECOMMEND_REASON,
        status=f"준비 완료 | 모델: {model} | UTF-8 한글 입력 지원",
    )


def update_inventory_summary(state, manager):
    count = len(manager.items)
    if count == 0:
        state.inventory_summary = EMPTY_INVENTORY_SUMMARY
    elif count == 1:
        state.inventory_summary = "냉장고에 식품 1개가 있습니다."
    else:
        state.inventory_summary = f"냉장고에 식품 {count}개가 있습니다."


def set_decision_view(state, label, title, reason):
    state.decision_label = label
    state.decision_title = title
    state.decision_reason = reason


def print_section(title):
    print(f"\n[{title}]")


def show_inventory(manager, state):
    print_section("현재 냉장고 목록")
    print(state.inventory_summary)

    if not manager.items:
        return

    for index, item in enumerate(manager.items, start=1):
        print(f"{index}. {item.name}")
        print(f"   냉장 보관 사유: {item.reason}")


def render_dashboard(state, manager):
    clear_screen()
    print("=" * 72)
    print("AI 냉장고 매니저")
    print("식품 추가, 보관 사유 확인, 냉장고 목록 관리, 메뉴 추천을 CLI에서 제공합니다.")
    print(f"상태: {state.status}")
    print("=" * 72)

    print_section("식품 추가")
    print("예: 김치, 우유, 두부, Greek yogurt. 한글과 영문을 모두 사용할 수 있습니다.")

    print_section("최근 판정 결과")
    print(f"상태 라벨: {state.decision_label}")
    print(state.decision_title)
    print(state.decision_reason)

    show_inventory(manager, state)

    print_section("추천 메뉴")
    print(state.recommend_title)
    print(state.recommend_reason)

    print_section("메뉴")
    print("1. 식품 추가")
    print("2. 메뉴 추천 받기")
    print("3. 종료")
    print("엔터. 화면 새로고침")


def handle_add_food(ai, manager, state):
    raw_food_name = prompt_input("\n추가할 식품 이름을 입력하세요: ")
    if raw_food_name is None:
        return False

    validation_error = validate_food_name(raw_food_name)
    if validation_error:
        set_decision_view(
            state,
            label="입력 확인",
            title="식품 이름을 다시 확인해 주세요.",
            reason=validation_error,
        )
        state.status = "입력값을 확인해 주세요."
        return True

    food_name = raw_food_name.strip()
    state.status = f"'{food_name}' 보관 여부를 AI가 확인하고 있습니다..."
    print(f"\n{state.status}")

    try:
        decision = ai.check_storage(food_name)
        result = manager.add_decision(decision)
    except AIResponseError as error:
        set_decision_view(
            state,
            label="오류",
            title="식품 판정에 실패했습니다.",
            reason=str(error),
        )
        state.status = str(error)
        return True
    except Exception:
        message = "AI 요청에 실패했습니다. API 키, 모델, 네트워크 상태를 확인해 주세요."
        set_decision_view(
            state,
            label="오류",
            title="식품 판정에 실패했습니다.",
            reason=message,
        )
        state.status = message
        return True

    if result.status == "added":
        set_decision_view(
            state,
            label="추가 완료",
            title=f"'{result.item_name}'을(를) 냉장고에 넣었습니다.",
            reason=result.reason,
        )
        state.status = f"'{result.item_name}' 추가 완료"
    elif result.status == "rejected":
        set_decision_view(
            state,
            label="추가 안 함",
            title=f"'{result.item_name}'은(는) 냉장고에 넣지 않았습니다.",
            reason=result.reason,
        )
        state.status = f"'{result.item_name}'은(는) 실온 보관 권장"
    else:
        set_decision_view(
            state,
            label="중복 항목",
            title=f"'{result.item_name}'은(는) 이미 목록에 있습니다.",
            reason=result.reason,
        )
        state.status = f"'{result.item_name}'은(는) 이미 등록되어 있습니다."

    update_inventory_summary(state, manager)
    return True


def handle_recommendation(ai, manager, state):
    if not manager.items:
        state.recommend_title = "추천할 재료가 아직 없습니다."
        state.recommend_reason = (
            "먼저 식품을 추가하면 그 재료를 기준으로 메뉴와 추천 이유를 보여줍니다."
        )
        state.status = "냉장고가 비어 있어 추천을 건너뛰었습니다."
        return True

    state.status = "AI가 현재 재료를 바탕으로 메뉴를 추천하고 있습니다..."
    print(f"\n{state.status}")

    try:
        recommendation = ai.recommend_menu(manager.items)
    except AIResponseError as error:
        state.recommend_title = "추천을 가져오지 못했습니다."
        state.recommend_reason = str(error)
        state.status = str(error)
        return True
    except Exception:
        message = "AI 요청에 실패했습니다. API 키, 모델, 네트워크 상태를 확인해 주세요."
        state.recommend_title = "추천을 가져오지 못했습니다."
        state.recommend_reason = message
        state.status = message
        return True

    state.recommend_title = recommendation.menu
    state.recommend_reason = recommendation.reason
    state.status = "메뉴 추천을 완료했습니다."
    return True


def main():
    configure_console_encoding()

    try:
        settings = load_settings()
    except ConfigError as error:
        print(f"설정 오류: {error}")
        return

    client = OpenAI(api_key=settings.api_key)
    ai = FridgeAI(client, settings.model)
    manager = FridgeManager()
    state = create_initial_state(settings.model)
    update_inventory_summary(state, manager)

    while True:
        render_dashboard(state, manager)
        choice = prompt_input("메뉴를 선택하세요: ")
        if choice is None:
            break

        choice = choice.strip()

        if not choice:
            continue

        if choice == "1":
            if not handle_add_food(ai, manager, state):
                break
        elif choice == "2":
            if not handle_recommendation(ai, manager, state):
                break
        elif choice == "3":
            print("프로그램을 종료합니다.")
            break
        else:
            state.status = "1~3 중에서 선택해 주세요."


if __name__ == "__main__":
    main()
