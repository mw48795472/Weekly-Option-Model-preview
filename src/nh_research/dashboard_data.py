"""Pure helpers for the offline Streamlit research dashboard."""
from __future__ import annotations

from math import exp, isfinite, log, pi, sqrt
import re

import numpy as np
import pandas as pd

from nh_research.analysis import forward_mean

HYPOTHESES = [
    ("H1", "위클리 도입 효과", "외부 사건자료 필요", "도입 종목의 log RV ATT", "실제 발표·개시일, 미도입 대조군, 현물 이력"),
    ("H2", "해외 모델 전이", "국내 기준모형 이후", "국내 단독 대비 테스트 손실 감소", "동기간 국내외 시계열, 상품 규격, 정보 가용시각"),
    ("H3", "커버드콜 공급", "외부 포지션 필요", "공급 변화에 따른 IV와 이후 RV", "펀드 계약별 signed 포지션, 설정·환매와 롤"),
    ("H4", "공포와 탐욕 국면", "인과와 예측 분리", "사전 국면별 ATT 또는 예측 손실", "사전 상태·여러 도입 사건 또는 훈련구간 국면"),
    ("H5", "만기 효과", "시세 확보 후 우선", "HAR 대비 만기 정보의 추가 가치", "역사 거래일·실제 만기·비만기 대조·장중 RV"),
    ("H6", "OI와 미래 변동성", "시세 확보 후 우선", "HAR 대비 OI 추가 손실 감소", "동일 범위 OI, 공표시각, 완결된 다음 5일 RV"),
    ("H7", "투자자 집중도", "외부 보유자료 필요", "옵션 활동과 보유집중의 상호작용", "개별 보유자·지분 변화·공표시점"),
    ("H8", "기관 리밸런싱", "외부 사건자료 필요", "노출변경 사건 전후 RV·IV·유동성", "사전 확정 목표비중, 실제 포지션, 사건 원장"),
    ("H9", "RFQ 추가 정보", "RFQ 로그 필요", "공개호가 대비 RFQ의 추가 정보", "요청·응답·체결·방향 정답 로그"),
    ("H9b", "단기 유동성 경보", "호가 수집 후", "다음 5분 유동성 스트레스 확률", "호가·잔량 이력, 수신상태와 결측 검열"),
]


def filter_contracts(frame, products, expiries, sides, query=""):
    selected = frame.loc[
        frame["under_name"].isin(products)
        & frame["expiry_date"].isin(expiries)
        & frame["option_side"].isin(sides)
    ]
    if query.strip():
        haystack = selected[["series", "product_name", "name_kor"]].astype(str).agg(" ".join, axis=1)
        selected = selected.loc[haystack.str.contains(query.strip(), case=False, regex=False)]
    return selected.copy()


def csv_bytes(frame):
    """Keep empty observations and string identifiers; provide an Excel UTF-8 BOM."""
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")


def gamma_curve(spot, strike, volatility_pct, days):
    """European Black–Scholes, r=q=0; hypothesis illustration, never market estimates."""
    if not all(isfinite(v) and v > 0 for v in (spot, strike, volatility_pct)):
        raise ValueError("Positive finite scenario inputs required")
    sigma = volatility_pct / 100
    result = []
    for day in days:
        if not isfinite(day) or day <= 0:
            raise ValueError("Time to expiry must be positive")
        t = day / 365
        d1 = (log(spot / strike) + sigma * sigma * t / 2) / (sigma * sqrt(t))
        result.append(exp(-d1 * d1 / 2) / sqrt(2 * pi) / (spot * sigma * sqrt(t)))
    return result


def index_windows(horizon=5):
    markers = list(range(25))
    old = pd.Series(markers, dtype=float).shift(-3).rolling(5).mean().shift(-5)
    correct = forward_mean(markers, horizon)
    return pd.DataFrame({"결정 인덱스 t": markers, "원본 미래창 마커 평균": old,
                         "수정 미래창 마커 평균": correct,
                         "수정 라벨 완결": [v is not None for v in correct]})


def report_section(text, hypothesis):
    pattern = rf"^### {re.escape(hypothesis)}:.*?(?=^### |^## |\Z)"
    match = re.search(pattern, text, re.M | re.S)
    return match.group(0) if match else "상세 내용은 통합 보고서를 참고하세요."


def markdown_for_browser(text, prefix):
    """Resolve repository-relative report links for the browser; external URLs stay intact."""
    from posixpath import normpath
    from urllib.parse import quote

    def replace(match):
        label, target = match.groups()
        target = target.strip("<>")
        if target.startswith(("https://", "http://", "#")):
            return match.group(0)
        relative = normpath("docs/" + target)
        return f"[{label}]({prefix}/{quote(relative, safe='/')})"
    return re.sub(r"\[([^\]]+)\]\((<[^>]+>|[^\s)]+)\)", replace, text)
