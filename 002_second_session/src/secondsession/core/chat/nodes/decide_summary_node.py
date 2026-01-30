# 목적: 요약 수행 여부를 결정한다.
# 설명: turn_count 기준으로 요약 경로를 선택한다.
# 디자인 패턴: 정책
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""요약 여부 결정 노드 모듈."""

from secondsession.core.chat.policy.error_route_policy import ErrorRoutePolicy
from secondsession.core.chat.policy.summary_route_policy import SummaryRoutePolicy
from secondsession.core.chat.state.chat_state import ChatState


def decide_summary_node(state: ChatState) -> dict:
    """요약 경로를 결정한다.

    TODO:
        - turn_count가 5를 초과하면 route를 "summarize"로 설정한다.
        - 그렇지 않으면 route를 "end"로 설정한다.
        - error_code가 존재할 때는 폴백 라우팅으로 전환하는 정책을 추가한다.
    """
    error_route = ErrorRoutePolicy().decide(state.get("error_code"))
    if error_route:
        return error_route

    turn_count = state.get("turn_count", 0)
    route = SummaryRoutePolicy().decide(turn_count)
    return {"route": route}
