"""
債務網路整理規劃（純計算，不涉及任何資料庫寫入）。

將 summary 中 multi-to-multi 的債務關係，重新規劃成「每個人最多只付款給一個人」
的結構（one-to-one / multi-to-one），藉此消除循環債務並減少轉帳筆數。

演算法：
1. 由所有兩兩債務算出每個人的淨額（net）。net > 0 代表別人欠他（債權人），
   net < 0 代表他欠別人（債務人）。循環債務在這一步會自然抵銷。
2. 每輪挑「待付金額最大」的人，把他待付的全額一次付給「待收金額最大」的人。
   - 付款者付完後即結清，之後不會再收款或付款，因此每人最多一筆付款（出度 ≤ 1）。
   - 收款者若因此收超過自己應收的金額，超出部分會成為他的待付金額，
     於後續輪次再整筆轉給另一個人（轉交）。
   - 已結清的人不會再被選為收款者，因此結果不會形成循環。
   最終轉帳筆數 ≤ 參與人數 - 1。
"""

from dataclasses import dataclass

from schemas.summary_data import Summary


@dataclass(frozen=True)
class Transfer:
    payer: int
    payee: int
    amount: int


def compute_balances(summaries: list[Summary]) -> dict[int, int]:
    """summary.amount > 0 代表 user2 欠 user1 amount 元。"""
    balances: dict[int, int] = {}
    for s in summaries:
        if s.amount == 0:
            continue
        balances[s.user1] = balances.get(s.user1, 0) + s.amount
        balances[s.user2] = balances.get(s.user2, 0) - s.amount
    return {uid: net for uid, net in balances.items() if net != 0}


def plan_settlement(summaries: list[Summary]) -> list[Transfer]:
    # excess > 0：還需要付出去的金額；excess < 0：還需要收進來的金額
    excess: dict[int, int] = {
        uid: -net for uid, net in compute_balances(summaries).items()
    }
    transfers: list[Transfer] = []

    while True:
        payers = [uid for uid, e in excess.items() if e > 0]
        if not payers:
            break
        receivers = [uid for uid, e in excess.items() if e < 0]
        # 總和恆為 0，有待付者就一定有待收者
        assert receivers, "unbalanced debt network"

        # 以 uid 作為次要排序鍵，確保結果具決定性
        payer = max(payers, key=lambda u: (excess[u], -u))
        payee = min(receivers, key=lambda u: (excess[u], u))
        amount = excess[payer]

        transfers.append(Transfer(payer=payer, payee=payee, amount=amount))
        excess[payer] = 0
        excess[payee] += amount

    return transfers
