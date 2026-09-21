# 自動再開用チェックポイント

専用worktree：`C:/Users/yuubi/.codex/worktrees/nontrivial-discovery/kyouen-1-to-9-classification`
ブランチ：`codex/nontrivial-discovery`

ユーザー依頼は、専用worktreeで未発見の非自明な事実を探索し、
5時間枠の制限解除後にも自動再開できるようにすること。
このタスクの毎時heartbeatは `automation`。リセットクレジットは使わない。

## 検証済みの成果

`DISCOVERY_CORNER_GATE_AND_COMPONENTS.md` を読む。
第四の角の大域的必要性、12石以上のグラフで最大配置が8ペアの成分に分かれること、
19点和集合内の幅11の静的障壁証明を発見。独立検証はPASS。
既に報告した成果を新発見として再通知しない。

## 続きの候補

1. floor 11で16個の最大配置が全部つながるか。まず明示的な経路を探す。
   floor 12とは局面数が大幅に増える可能性がある。状態数とメモリを制限し、
   上限打切りを不可能性と取り違えない。必要ならC++へ移す。
2. 角禁止の250局面成分に対する短い幾何学的証明。
   まず静的占有数の分離条件を探し、得られた候補を独立に検証する。

前回終了時にバックグラウンド計算はない。初めに念のためプロセスを確認する。
1回の再開では上記の一つを選び、結果・不成立・打切りを区別して保存する。
意味のある追加結果が得られたら報告し、自動継続の目的を達成したとしてheartbeatを停止する。
新しい結果がなくてもチェックポイントは更新し、同じ無成果の計算を繰り返さない。

## 再検証

`python night-research/verify_corridor_discovery.py`

証明書は `results/discovery_*.json`、探索と独立検証は `night-research/*corridor*.py`。
元のユーザー作業ディレクトリは変更していない。
