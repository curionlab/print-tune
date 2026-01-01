# src/printtune/core/session_loop.py
from __future__ import annotations

from dataclasses import replace
from typing import Literal, Optional
import random

from .log_types import SessionRecord, RoundRecord, now_iso
from .ids import RoundId, SessionId
from .optimizer.candidate_factory import make_candidates_from_X, x_to_globals
from .optimizer.param_space_v1 import PARAM_KEYS_V1
from .botorch.update_loop import propose_from_session_for_round

Intent = Literal["pairwise_explore", "rejudge", "reprint"]

def _next_round_index(session: SessionRecord) -> int:
    return len(session.rounds) + 1

def _new_round_id(session: SessionRecord, round_index: int) -> RoundId:
    return RoundId.new(SessionId(session.session_id), round_index=round_index)

def append_round(session: SessionRecord, rr: RoundRecord) -> SessionRecord:
    return replace(session, rounds=list(session.rounds) + [rr])

def _extract_x_from_candidate(c) -> list[float]:
    # globals 前提でXを抽出
    g = c.params.get("globals")
    if g is None:
        # 移行期ガード（万一古いデータがあれば）
        raise ValueError("candidate params missing 'globals'")
    return [float(g[k]) for k in PARAM_KEYS_V1]

def make_next_round(
    session: SessionRecord,
    intent: Intent,
    rubric: Optional[str] = None,
    delta_scale: float = 1.0,
) -> SessionRecord:
    round_index = _next_round_index(session)
    rid = _new_round_id(session, round_index)

    # 1. pairwise_explore: BoTorch提案を使う（基本ルート）
    if intent == "pairwise_explore":
        proposal = propose_from_session_for_round(session, round_index)
        
        cands = make_candidates_from_X(
            round_id=rid,
            slots=["A", "B"],
            X=proposal.X_next
        )
        
        rr = RoundRecord(
            round_id=rid.value,
            round_index=round_index,
            created_at=now_iso(),
            candidates=cands,
            mode="pairwise",
            purpose="pairwise_explore",
            rubric=rubric,
            delta_scale=1.0,
            meta={"schedule": proposal.schedule},  # metaにスケジュール保存
        )
        return append_round(session, rr)

    # 直前ラウンド情報を取得（rejudge/reprint用）
    prev = session.rounds[-1]
    #prev_X: list[list[float]] = []
    
    # 候補が2つ以上ある前提だが、万一足りない場合は安全策で複製するなどのガードが必要かも
    # ここでは既存ロジック通り先頭2つを取得
    #source_cands = prev.candidates if len(prev.candidates) >= 2 else prev.candidates * 2
    #for c in source_cands[:2]:
    #    prev_X.append(_extract_x_from_candidate(c))


    # 2. rejudge: 直前と同じXで再生成（スロット振り直し等は make_candidates_from_X が新規ID発行で対応）
    # dev3で、rejudgeは観点を指定したchosenの位置づけに変更したため、削除
    """
    if intent == "rejudge":
        # 直前の全候補をそのままコピーしてIDだけ振り直す
        # (OAなら4つ、Pairwiseなら2つ、そのまま引き継ぐ)
        prev_X = [_extract_x_from_candidate(c) for c in prev.candidates]
        slots = [c.slot for c in prev.candidates] # スロット名も引き継ぐ
        
        cands = make_candidates_from_X(rid, slots=slots, X=prev_X)

        rr = RoundRecord(
            round_id=rid.value,
            round_index=round_index,
            created_at=now_iso(),
            candidates=cands,
            mode=prev.mode,
            purpose="rejudge",
            rubric=rubric,
            delta_scale=1.0,
            meta={"source_round": prev.round_index},  # 追跡用meta
        )
        return append_round(session, rr)
    """
    
    # 3. reprint: 探索幅を増やして少し動かす（簡易ロジック）
    # ※ 本来は軸スケジュールと連動させるべきだが、一旦P0ロジック（Exposure中心）を維持しつつglobals対応
    
    delta = 0.35 * float(delta_scale)
    def clamp(v: float) -> float:
        return max(-2.0, min(2.0, v))

    # ★ OAモードの場合の特別処理 ★
    if prev.mode == "oa":
        # 全ての候補に対して、Exposure(index 0)を一律にずらす（例：全体的に明るく/暗く）
        # ※ 本当は各候補の分布を広げる等の戦略もあり得るが、
        #    Reprintの動機は「全体的にダメ（暗すぎ/色変）」が多いので、一律シフトが直感的。
        
        new_X = []
        for c in prev.candidates:
            base = _extract_x_from_candidate(c)
            # 全候補の Exposure (index 0) に delta を加算
            # deltaが正なら全体を明るく、負なら暗くする方向だが、
            # reprintのdeltaは「大きさ」なので、方向はランダムか固定か悩ましい。
            # ここでは「現状の平均」を見て...といきたいが、
            # シンプルに「Exposureを +delta する版」を出す（明るくしてみる）
            # もしくは、L4の各点に対して「分布を広げる」方がOAらしいか？
            
            # 案: 単純に「前回の全候補の Exposure に delta を足す」
            # (暗すぎた場合に有効。明るすぎた場合は逆だが、UIで方向指定がないので正方向に振る)
            shifted = [
                clamp(base[i] + (delta if i == 0 else 0.0)) 
                for i in range(len(base))
            ]
            new_X.append(shifted)
            
        cands = make_candidates_from_X(rid, slots=[c.slot for c in prev.candidates], X=new_X)
        
    else:
        # Pairwise (2候補) の場合
        # 直前の A (index 0) を基準に、±delta で開き直す（既存ロジック）
        prev_X_A = _extract_x_from_candidate(prev.candidates[0])
        X2 = [
            [clamp(prev_X_A[i] + (delta if i == 0 else 0.0)) for i in range(len(prev_X_A))],
            [clamp(prev_X_A[i] - (delta if i == 0 else 0.0)) for i in range(len(prev_X_A))],
        ]
        cands = make_candidates_from_X(rid, slots=["A", "B"], X=X2)

    rr = RoundRecord(
        round_id=rid.value,
        round_index=round_index,
        created_at=now_iso(),
        candidates=cands,
        mode=prev.mode, # モード継承 (OAならOAのまま)
        purpose="reprint",
        rubric=rubric,
        delta_scale=float(delta_scale),
        meta={"source_round": prev.round_index, "delta_applied": delta},
    )
    return append_round(session, rr)