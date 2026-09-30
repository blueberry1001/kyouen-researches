"""Lossless original-hypothesis inventory plus explicitly reviewed evidence.

Legacy labels are evidence pointers, never an automatic settled verdict.
The reviewed map is deliberately conservative: unreviewed is not unresolved.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BANKS = [ROOT.parent/'hypothesis-bank-2026-09-27.md',
         ROOT.parent/'hypothesis-bank-round2-2026-09-27.md']
ORIGINAL = re.compile(r'^- \*\*(B\d{3}) \[([^]]+)\] (.*?)\*\* (.+)$')
ID = re.compile(r'B\d{3}(?!\d)')
LABEL = re.compile(r'(?<![A-Z-])(SUPPORTED|REFUTED|PARTIAL|INCONCLUSIVE|NOT-CHECKED)(?![A-Z-])')
REVIEWED = {}


def atomic_text(path, text):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         dir=path.parent, prefix=path.name+'.', suffix='.tmp',
                                         delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def review(ids, status, kind, source, reason, additional=()):
    for bid in ids.split():
        assert bid not in REVIEWED
        REVIEWED[bid] = {'original_status': status, 'evidence_kind': kind,
                         'preferred_report': source, 'reason': reason,
                         'additional_reports': list(additional)}


review('B098', 'SUPPORTED', 'complete_small_board_saturation_jump',
       'round54-small-board-saturation-jump.md',
       '原文にn≥4の指定なし。全n2/n3集合の監査でs2=3・s3=5、差2の存在を証明。n≥4を追加した問いの決着は主張しない。')
review('B097', 'PARTIAL', 'complete_finite_saturation_sequence',
       'round54-small-board-saturation-jump.md',
       '完全に確認したs1..s9=1,3,5,5,5,6,7,8,9では単調。s10∈[8,10]で九盤以後の単調性は未決。')
review('B095 B096', 'PARTIAL', 'general_asymptotic_lower_exponent_proof',
       'round52-general-saturation-exponent-lower-bound.md',
       '原始方向別に直線被覆O(n k^(3/2))、三点真円の整数係数と約数上界でR(n)=n^o(1)。全ε>0でs_n>n^(2/3−ε)を証明。対応する上界・s_n=o(n)は未証明。')

review('B079', 'PARTIAL', 'exact_geometric_cover_incidence_maximization',
       'round48-six-stone-cover-incidence.md',
       '十盤六石の重複被覆総数は全安全集合最大85<必要94、等号証人を独立検算。上界は完全最適化に依存し、原文の短い非列挙証明は未達。')
review('B094', 'REFUTED', 'independently_verified_ten_stone_maximal_witness',
       'round49-ten-stone-maximal-counterexample.md',
       '十盤S=[21,27,31,35,36,46,65,81,29,48]は全210四点安全・全90空点禁止、s10≤10で原文11を反証。')
review('B093', 'PARTIAL', 'complete_seven_stone_exclusion_and_ten_stone_witness',
       'round51-ten-board-seven-stone-exclusion.md',
       's9=9から十盤七石候補の全幅帰着、初点0..4全5.9億節点を完了してs10≥8。健全な十石証人で[8,10]、八・九石は未決。',
       ('round49-ten-stone-maximal-counterexample.md',))

review('B091', 'SUPPORTED', 'complete_all_lower_sizes_exclusion_and_finite_witness',
       'round46-small-saturation-and-window-reduction.md',
       '8×8のk≤4は三つ組補完上界、k5/6/7は個別の完全探索で除外。八石極大証人を独立幾何で検算しs8=8。')
review('B092', 'SUPPORTED', 'complete_lower_sizes_exclusion_and_window_orbit_exhaustion',
       'round46-small-saturation-and-window-reduction.md',
       '9×9のk≤7を除外、九石証人を検算。408配置の全1632埋め込みに合法外点、八石候補の初点をD4で0..4へ帰着し全19.5億節点探索が完了、s9=9。')
review('B077 B080', 'SUPPORTED', 'finite_witness_and_general_minimum_stone_count_proof',
       'round47-private-cover-and-global-minima.md',
       '4×4の全空点二重以上六石証人・完全一重被覆五石証人を独立検算。曲線上界と残る小盤の全域検査で最小石数6/5、最小盤4を証明。')
review('B078 B361', 'SCOPE_UNCLEAR', 'degenerate_endpoint_and_complete_finite_nondegenerate_support',
       'round47-private-cover-and-global-minima.md',
       'n1の全占有最小極大には空点なし、B078の存在節は偽・ρは未定義。非空空点の読みはn2..8全最小極大でmin b1・ρ1、n≥9一般命題は未証明。',
       ('round50-nine-board-private-point-family.md',))


review('B349', 'SUPPORTED', 'general_minimum_classification_and_finite_realizations',
       'round40-b349-minimum-four-edge-classification.md',
       '二点競合ありの最小合法点数5・全9型を証明し全型を格子実現。競合なしを含める読みの最小4・単独辺1型も分類。')
review('B057 B441 B443', 'REFUTED', 'complete_exact_family_counterexample',
       'round42-exact-residual-family-audit.md',
       '4×4四石・同一L/Rの完全族は二集合のみ。三石交換が必要、Rは連結な四点パス。全65536集合から抽出。')
review('B444 B446 B449', 'SUPPORTED', 'complete_exact_family_witness',
       'round42-exact-residual-family-audit.md',
       '非空連結Rの分裂、同一族別成分で最大一石解除数8対7、厳密抽象同型40集合の四成分分裂を検算。B446旧反証を訂正。')
review('B448', 'PARTIAL', 'general_four_stone_bridge_proof',
       'round42-exact-residual-family-audit.md',
       '任意の安全四石配置対は常に安全な三石層のJohnsonグラフを通って結べる。k≥5の原文全体は未証明。')
review('B350', 'SUPPORTED', 'finite_witness_and_general_minimum_legal_size_proof',
       'round43-b350-value-preserving-move-switch.md',
       '5×5の合法5点で両版g1・勝ち手1対5。全m≤4極小残余族を二方式全列挙し最小合法点数5、n≤3全域除外と4×4証人で最小盤4。')
review('B062', 'REFUTED', 'infinite_clique_family_and_minimum_board_counterexample',
       'round44-three-stone-cliques-and-tree-minima.md',
       '三石の標準整数盤に任意大のK4Mを実現、彩色数は無界。4×4初例は厳密χ6、全n≤3三石は三色で最小盤4。')
review('B064', 'SUPPORTED', 'finite_witness_and_general_minimum_legal_size_proof',
       'round44-three-stone-cliques-and-tree-minima.md',
       '3×3のP5+一三点辺でg0対3、最小盤3。木の勝敗反転の最小合法点数5を証明。値だけの変更の最小4と区別。')
review('B344', 'PARTIAL', 'minimum_connecting_tree_classification',
       'round44-three-stone-cliques-and-tree-minima.md',
       '効く三点辺の最小接続木はK1,3・三葉上の辺、格子実現を検算。大きな木の距離偶奇による一般分類は未証明。')
review('B071 B072 B075', 'SUPPORTED', 'general_geometric_proof_and_sharpness_certificates',
       'round45-cover-gap-and-sharp-overlap.md',
       '三点族の線形性と点対計数、異なる曲線の交点数で全盤証明。k≥4の改善上限−1、六石等号、二空点交差の最小石数6も検算。')
review('B073', 'REFUTED', 'general_impossibility_using_melchior_inequality',
       'round45-cover-gap-and-sharp-overlap.md',
       '反転後の通常直線数δ≥3。全k≥4で床付き二次上限から必ず1減り、床等号もSteiner等号も不可能。')


review('B211 B212 B215 B216 B220 B541 B546 B550', 'SUPPORTED', 'general_proof',
       'round4-fixed-width.md', '全固定幅の一様終局定理。必要な短い二行盤と区間証人も全数検査。')
review('B213 B219 B544 B555 B556', 'REFUTED', 'general_impossibility',
       'round4-fixed-width.md', '固定幅の全極大サイズ3w・全局面偶奇式により、原文の無限量化を除外。')
review('B542', 'SUPPORTED', 'general_proof_and_finite_certificate',
       'round4-two-row-order-strategy.md', 'm=6..8の順序型表と全m≥9の一般証明。旧PARTIALは上書き。')
review('B141 B145 B150 B471 B472 B473', 'SUPPORTED', 'general_proof',
       'round4-collinear-asymptotic.md', '整数方向別の恒等式と一様誤差による漸近証明。B141の旧REFUTEDを訂正。')
review('B074', 'REFUTED', 'infinite_counterexample_family',
       'round5-quadratic-cover.md', '安全格子の無限族でb/k→∞、絶対定数の線形上界を反証。')
review('B356', 'SUPPORTED', 'infinite_witness_family',
       'round5-quadratic-cover.md', '安全二コピーの合併補題で二空点の固定二次下界。round24は別証明。',
       ('round24-circular-cubic-multiple-cover.md',))
review('B357', 'REFUTED', 'infinite_counterexample_family',
       'round7-parabola-cover.md', '固定εでも高被覆空点数Ω(k)。二次幅の整数盤。round24は別証明。',
       ('round7-ellipse-cover.md', 'round24-circular-cubic-multiple-cover.md'))
review('B360', 'SUPPORTED', 'infinite_witness_family',
       'round5-cover-union.md', '同盤・同石数・双方bmax=Θ(k²)で禁止点和集合比が無界。')
review('B557', 'REFUTED', 'finite_exhaustion_and_witness',
       'round5-row-thresholds.md', '五行幅11の不存在と幅12の安全15石。全称のw=5反例。')
review('B558', 'SUPPORTED', 'general_proof',
       'round8-ap-quadratic-prime.md', '全wに対する素数公差の三点AP、幅O(w²)。旧公差1候補の未証明と区別。')
review('B351 B354 B355', 'SUPPORTED', 'general_proof_using_published_theorems',
       'round6-rational-orchard.md', '反転・安全化補題、Green–TaoとMazurの適用条件を確認した一般証明。')
review('B353', 'REFUTED', 'general_impossibility_using_published_theorems',
       'round6-rational-orchard.md', '有理点のδ/k→∞で、原文の線形欠損の無限族を除外。')
review('B352', 'PARTIAL', 'partial_general_bound',
       'round6-rational-orchard.md', 'δ>k(log log k)^ηは固定冪k^(1+ε)の下界ではない。')
review('B381 B382', 'SUPPORTED', 'finite_complete_classification',
       'round9-n7-outer-patterns.md', '既存全16最大配置の全外点を二方式で照合し、最初の半径2の型を分類。')
review('B386', 'REFUTED', 'finite_counterexample',
       'round9-n7-n8-overlap.md', '7×7最大から一石除去・二石追加で8×8安全15石。')
review('B387', 'SUPPORTED', 'finite_exhaustion_and_witness',
       'round9-n7-n8-overlap.md', '全16最大・全埋込みでA型の最小除去1、B型2。既知K8=15を使用。')
review('B388', 'SUPPORTED', 'general_proof',
       'round9-external-rays.md', '二乗直径による円の外接領域上界と、遠方直線だけの合法外点算法。')
review('B384 B385 B390', 'PARTIAL', 'finite_evidence_and_partial_general_result',
       'round16-dilation-exterior.md', '拡大後r=1は最大性・最小極大性・一石移動を保存せず、原文は未決着。')
review('B376', 'REFUTED', 'finite_exhaustion',
       'round10-small-saturation.md', '8×8全408安全8石極大に被覆曲線13本以上。貪欲上界を下界に使わない。')
review('B377 B379', 'SUPPORTED', 'finite_exhaustion_and_witness',
       'round10-small-saturation.md', '7石一合法点の縮約と、8石から9×9の9石極大への具体的拡張。')
review('B453', 'SUPPORTED', 'general_proof',
       'round10-circle-denominator.md', '分母素因数型と剰余類の完全格子点数上界、q=3/4の等号。')
review('B454', 'REFUTED', 'finite_counterexample_and_exhaustion',
       'round12-b454-counterexample.md', 'm=11で奇分母q=11のスパン161を実現し、全2冪分母候補を除外。')
review('B455', 'REFUTED', 'general_impossibility',
       'round11-residue-orbits.md', 'q≥3の剰余類は90度回転の四個組。一つだけが厳密最大にはならない。')
review('B456', 'SUPPORTED', 'general_proof',
       'round11-circle-records.md', '固定分母の記録円に必要な平方類が無限。過去の最良円の整数拡大を除外。')
review('B461 B463 B465 B467', 'SUPPORTED', 'general_proof',
       'round4-circle-windows.md', '完全円の可変サイズ整数窓のスペクトルと一点削除の必要十分条件。')
review('B464', 'REFUTED', 'general_impossibility',
       'round4-circle-windows.md', '完全格子円の長方形窓・正方形窓スペクトルは常に一致。')
review('B462 B470', 'SUPPORTED', 'general_reduction_and_finite_exhaustion',
       'round4-circle-windows.md', '候補縮約を証明しn≤12を整数全走査。11点の最初の盤は11×11。')
review('B457', 'PARTIAL', 'partial_general_spectrum_result',
       'round4-circle-windows.md', '全サイズ和集合と固定窓の穴に一般結果。原文の同点数での統計比較は未完了。')
review('B458', 'SCOPE_UNCLEAR', 'counterexample_to_precise_subclaim',
       'round16-first-appearance.md', '指定要約量で四点初出が決まる強い読みは反証。「短く分類」の原文全体は未指定。')
review('B468', 'SCOPE_UNCLEAR', 'counterexample_to_monotonic_reading',
       'round4-circle-windows.md', '同完全点数・同スパンで単調性の反例。統計傾向には追加の母集団指定が必要。')
review('B142', 'REFUTED', 'general_asymptotic_refutation_using_published_theorem',
       'round17-original-scope-audit.md', '公刊C_n=Θ(n^5)は原文n^(4+o(1))と両立しない。n^6ではない。')
review('B475', 'SUPPORTED', 'general_proof_using_published_count',
       'round13-four-point-circles.md', '四点重みで盤内点数4へ集中。完全円上点数と区別。')
review('B476', 'REFUTED', 'general_asymptotic_refutation',
       'round13-four-point-circles.md', '四点重みの平均点数は4へ収束し、発散しない。')
review('B477', 'SUPPORTED', 'general_identity',
       'round15-standard-chord.md', '標準弦の原始方向・整数内積・既約分数による重複なし計数。')
review('B478', 'SUPPORTED', 'general_proof_using_published_count',
       'round13-poisson-limit.md', '固定kの依存辺評価でPoisson極限。有限nの束は反例にならない。')
review('B479', 'REFUTED', 'general_asymptotic_refutation',
       'round13-poisson-limit.md', '同尺度の束の確率は0へ。非自明な複合Poissonにはならない。')
review('B480', 'SUPPORTED', 'general_asymptotic_expansion',
       'round14-safety-correction.md', 'log安全確率の次項を三点共有の禁止ペアから導出。')
review('B089', 'REFUTED', 'general_asymptotic_refutation',
       'round17-b089-bounded-degree.md', '固定本数低次数曲線のo(n)上界と素数盤のK_n線形下界。')
review('B070 B261 B266', 'SUPPORTED', 'general_proof_and_infinite_construction',
       'round18-pair-synergy.md', '二手相乗を石ごとの一般化円へ分解し、無界の利得を整数格子で実現。')
# B070 has its own proof, not the pair-synergy report.
REVIEWED['B070'].update(preferred_report='round18-competition-stars.md',
                         reason='固定kのクリーク分割辺の和。全kで誘導星の禁止と鋭い整数実現。')
review('B227', 'REFUTED', 'general_impossibility',
       'round18-equal-passes.md', '両者各一回の未使用パス権で開始。同数有限パスの後追い応答。履歴の不均等状態と区別。')
review('B063', 'SUPPORTED', 'general_lower_bound_and_finite_witness',
       'round19-b063-stone-hierarchy.md', '誘導K1,4は三石で不可能、四石で実現。最小頂点数5も全型で確認。')
review('B253 B522', 'SUPPORTED', 'finite_witness_and_exhaustion',
       'round19-rule-removal-audit.md', '全単独・全ペア解除を除外し、三組解除の全真部分族と真のmexを検算。')
review('B255', 'SUPPORTED', 'finite_witness_and_minimum_board_proof',
       'round20-b255-maximum-preserving-flip.md', '5×5で最大サイズ9・全100最大配置を保存して反転。4×4以下は不可能。')
review('B224', 'SUPPORTED', 'finite_witness',
       'round21-b224-ten-curves.md', '5×5の四円・六直線で標準の非空勝ち初手9点を完全保存。最小本数とは言わない。')
review('B228', 'SUPPORTED', 'finite_witness',
       'round22-b228-circle-thresholds.md', '全直線を保持し円を点数降順に丸ごと追加、空盤g=2→0→2。')
review('B252', 'SUPPORTED', 'finite_witness',
       'round22-b252-one-circle-versus-scattered.md', '4×4で一円全70解除だけが反転。散在70解除では保存。')
review('B256', 'REFUTED', 'general_impossibility',
       'round23-b256-symmetric-minimum.md', '全nで非空最小族1または2をD4不変な互いに素な四点組が達成。')
review('B258', 'SCOPE_UNCLEAR', 'general_result_with_quantifier_ambiguity',
       'round23-b256-symmetric-minimum.md', '全n≥4に共通必須型なし。n=2を存在量化に含む読みは自明に真で、全体判定は保留。')
review('B251', 'PARTIAL', 'finite_exhaustion',
       'round32-b251-seven-board-exclusion.md', '7×7全6364単独解除を935軌道・二方式で除外。共有標準表全179810350局面の証明条件も検算。存在証人はn≥8。',
       ('round23-b251-six-by-six-exclusion.md',))
review('B333', 'REFUTED', 'finite_counterexample_and_minimum_board_proof',
       'round25-forced-length-holes.md', '6×6でWFT={7,11}、9なし。n≤5全状態の二方式検査。')
review('B031', 'REFUTED', 'finite_counterexample_and_minimum_board_proof',
       'round25-forced-length-holes.md', '6×6でT*={7,11}、9なし。旧n=5反例T*={6,7,9}は偶奇混在で不可能。')
review('B334', 'SUPPORTED', 'finite_witness_and_minimum_board_proof',
       'round25-forced-length-holes.md', '6×6の3石N局面でT*={6,8,10}、WFT空。固定長AND/ORでも確認。')
review('B022 B315', 'SUPPORTED', 'finite_complete_classification_and_witness',
       'round28-seven-board-original-verdicts.md', '7×7全179810350安全局面を二方式で照合。σ7=4、J7中央は関節点。')
review('B040 B313 B314', 'REFUTED', 'finite_counterexample_and_complete_verification',
       'round28-seven-board-original-verdicts.md', '7×7空盤WFTは空。四隅の唯一の応答先が中央で、近完全マッチングなし・橋四本。')
review('B006 B016 B021 B319 B321 B322 B331 B335', 'PARTIAL', 'finite_complete_classification',
       'round28-seven-board-original-verdicts.md', '7×7までの一石・飽和・J・空盤WFTを完全検査したが、原文の無界全称は未証明。')
review('B362 B367 B369', 'SUPPORTED', 'finite_witness',
       'round29-fault-witness-audit.md', '独立幾何で原文の故障耐性・解除割合・最大集合不要石の具体的証人を照合。旧決着の監査。')
review('B368', 'REFUTED', 'finite_counterexample_and_exhaustion',
       'round29-fault-witness-audit.md', '3×3全512部分集合の極大は全て5石。最小極大の石2を除いても元の空点は全て禁止。')
review('B047', 'REFUTED', 'finite_counterexample_with_exact_residual_game',
       'round31-b047-odd-cycle-counterexample.md', '5×5の6石から残余C5を正確に実現。頂点推移的Pで合法点5個なので固定点なしの応答対合は不可能。')
review('B343', 'SUPPORTED', 'finite_witness_with_sole_triple_and_full_certificate',
       'round33-b343-single-triple-switch.md', '6×6でRの三点辺がちょうど一つ。単独除去でg=1→3、勝ち手{14}→{15,19}は互いに素。全256拡張を独立検算。')
review('B067', 'REFUTED', 'finite_counterexample_with_exact_height',
       'round34-b067-induced-seven-cycle.md', '4×4でh=3の全256拡張を検査。二点競合の誘導C7に弦なし。旧K(S)の計算バグの留保を解消。')
review('B068', 'SUPPORTED', 'finite_cospectral_witness_pair',
       'round34-b068-cospectral-opposite-games.md', '6×6の二点残余のみの8頂点対で次数列・厳密特性多項式が一致、g=3と0。両256拡張と多項式行列式を独立検算。')
review('B524', 'SUPPORTED', 'finite_witness_and_cardinality_minimum_proof',
       'round35-empty-intersection-minimum.md', '4×4で三組の共通点が空、全三組だけg=0→2。全8部分族全安全局面の独立mex一致と既存全単独・全ペア除外で基数最小。')
review('B523', 'REFUTED', 'cardinality_minimum_counterexample',
       'round35-empty-intersection-minimum.md', '基数最小の三組反転解除族の共通部分が空。共有三点を要求する全称への反例。',
       ('round19-rule-removal-audit.md',))
review('B521', 'SUPPORTED', 'finite_complete_exhaustion',
       'round19-rule-removal-audit.md', '4×4全18721二組解除を2554D4軌道で検査し全てP。既存原文決着の採用。')
review('B501 B506', 'REFUTED', 'exact_rational_finite_counterexamples',
       'round36-random-original-witness-audit.md', '既存P証人を独立整数幾何・全継続Fraction再帰で再検算。5×5でp=2383/3360>2/3、4×4のh3で76/135>1/2。')
review('B502', 'SUPPORTED', 'exact_rational_finite_witness',
       'round36-random-original-witness-audit.md', '6×6のP証人mask35652737、p=5162/6615>3/4。全115安全拡張のg・p・hを厳密検算。既存決着の採用。')
review('B342', 'REFUTED', 'finite_counterexample_with_forest_and_single_deletion',
       'round37-residual-original-witness-audit.md', '4×4のS=[0,2]、二点競合は五辺マッチング。極小三点辺[1,10,12]の単独除去でg=5→0を独立全安全mex検算。')
review('B346', 'SUPPORTED', 'finite_pair_synergy_witness',
       'round37-residual-original-witness-audit.md', '3×3のS=[0,1,4]、極小三点辺二つの単独除去はg0、同時除去だけg3。既存証人を原文照合・全安全mex再検算。')
review('B525', 'REFUTED', 'finite_whole_circle_counterexample',
       'round22-b252-one-circle-versus-scattered.md', '4×4の中央八点真円の全70四点組を丸ごと解除し空盤g=0→1。既存B252証人はB525の全称にも直接反例。')
review('B345', 'REFUTED', 'sole_minimal_triple_counterexample_and_minimum_legal_size',
       'round38-b345-sole-triple-clique-counterexample.md', '5×5のR=一二点辺+一三点辺。二点競合はK2+K1+K1、唯一の三点辺でg=1→3。全16拡張検算、非退化の最小合法点数4。')
review('B065', 'SUPPORTED', 'finite_witness_and_minimum_board_proof',
       'round41-b065-pair-empty-grundy-five.md',
       '8×8で二点辺0・合法7点・g=5。全128拡張を四方式、全67安全mexを三方式検算。n≤7全域除外と合わせ最小盤8。',
       ('round39-b065-seven-board-exclusion.md',))
review('B325 B326', 'PARTIAL', 'finite_complete_census_and_small_board_crosscheck',
       'round30-ceiling-orbit-finite-audit.md', '7×7全安全局面の天井・軌道・余裕を計算。B325の無限族とB326の全盤条件は未決着。')
review('B011 B015 B018 B301 B302 B303 B305 B307 B308 B309 B311', 'SUPPORTED',
       'finite_complete_classification_and_witness', 'round27-fixed-response-audit.md',
       '原文の固定盤量化を全状態再計算・全グラフ構成で検査。無限の全盤主張へ外挿しない。')
review('B012 B013 B014 B304 B306', 'REFUTED', 'finite_complete_classification',
       'round27-fixed-response-audit.md', 'J5全20辺と全マッチングを検査。B306は単一16交替サイクルで、旧説明を訂正。')
review('B317', 'SUPPORTED', 'finite_witness_and_exhaustive_certificates',
       'round27-fixed-response-audit.md', '4×4全112212完全マッチングが4/6手目で破れる。全証明書と逆順独立列挙で網羅。')


def main():
    originals = {}
    hashes = {}
    for bank in BANKS:
        lines = bank.read_text(encoding='utf-8-sig').splitlines()
        hashes[str(bank.relative_to(ROOT.parent))] = hashlib.sha256(bank.read_bytes()).hexdigest()
        section_title, section_start = '', 0
        for line_no, line in enumerate(lines, 1):
            if line.startswith('## '):
                section_title, section_start = line[3:], line_no
            match = ORIGINAL.match(line)
            if match:
                bid, kind, title, claim = match.groups()
                assert bid not in originals
                originals[bid] = {'id': bid, 'bank': str(bank.relative_to(ROOT.parent)),
                                  'original_line': line_no, 'original_exact_line': line,
                                  'tag': kind, 'title': title, 'claim': claim,
                                  'section_title': section_title, 'section_line': section_start,
                                  'section_setup': '\n'.join(lines[section_start:line_no-1]).split('- **B')[0].strip(),
                                  'evidence_pointers': []}
    assert set(originals) == {f'B{i:03}' for i in range(1, 601)}
    for path in sorted(ROOT.glob('*.md')):
        if path.name.startswith('round26') or path.name in {'CONTINUATION-kyouen-hypotheses.md'}:
            continue
        lines = path.read_text(encoding='utf-8-sig').splitlines()
        for i, line in enumerate(lines):
            if not re.match(r'^#{1,6}\s+B\d{3}', line):
                continue
            heading_ids = ID.findall(line)
            if re.search(r'B\d{3}\s*[-–〜]\s*B\d{3}', line):
                continue  # batch/range headers do not assign one verdict to every member
            end = next((j for j in range(i+1,len(lines)) if lines[j].startswith('#')),len(lines))
            labels = [{'line': j+1, 'labels': LABEL.findall(lines[j]), 'exact_text': lines[j]}
                      for j in range(i+1,end) if LABEL.search(lines[j]) and
                      any(word in lines[j] for word in ('判定','原命題','弱化版','SUPPORTED','REFUTED'))]
            pointer = {'report': path.name, 'heading_line': i+1, 'heading': line,
                       'joint_heading_ids': heading_ids, 'labels_in_section': labels,
                       'weakening_mentioned': any('弱化' in z for z in lines[i:end])}
            for bid in heading_ids:
                if bid in originals:
                    originals[bid]['evidence_pointers'].append(pointer)
    for bid, row in originals.items():
        row.update(REVIEWED.get(bid, {'original_status': 'NOT_AUDITED', 'evidence_kind': 'unreviewed',
                                     'preferred_report': None, 'reason': '旧ラベルの再集計だけでは原文決着を採用しない。',
                                     'additional_reports': []}))
        if row['preferred_report']:
            for report in [row['preferred_report']]+row['additional_reports']:
                assert (ROOT/report).is_file(), report
    rows = [originals[f'B{i:03}'] for i in range(1,601)]
    counts = dict(Counter(row['original_status'] for row in rows))
    reviewed_count = 600-counts.get('NOT_AUDITED',0)
    payload = {'total_originals': 600, 'reviewed_originals': reviewed_count,
               'counts_are_audit_states_not_total_unresolved': True, 'audit_state_counts': counts,
               'original_source_sha256': hashes,
               'index_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'rows': rows}
    report_names = {p['report'] for row in rows for p in row['evidence_pointers']}
    report_names |= {row['preferred_report'] for row in rows if row['preferred_report']}
    report_names |= {p for row in rows for p in row['additional_reports']}
    payload['evidence_report_sha256'] = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                        for name in sorted(report_names)}
    atomic_text(ROOT/'round26_original_scope_index.json',json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    lines = ['# 全600原命題の証拠索引（原文監査は途中）','',
             '更新: 2026-10-01。原文600件を重複・欠落なく抽出し、原文と証拠への参照を固定した。',
             '**未監査は未解決と同義ではない。この表から研究全体の未解決数はまだ確定できない。**','',
             f'原文照合して採用した記録は{reviewed_count}件。残りは旧ラベルを採用せずNOT_AUDITEDとする。',
             '旧個票の原命題・弱化版ラベルはJSONのevidence_pointersに行番号・原文ごと保存した。',
             '最も強いラベルを自動選択したり、弱化版を原命題へ昇格したりしていない。',
             'SUPPORTEDは原文の量化を満たす記録、REFUTEDはその反証記録。PARTIALは明示した部分結果。',
             'SCOPE_UNCLEARは原文の解釈・統計母集団が足りず、より強い読みの反証だけでは全体を決めないもの。','',
             '## 監査状態の内訳','', '| 状態 | 件数 |','|---|---:|']
    lines += [f'| {status} | {count} |' for status,count in sorted(counts.items())]
    lines += ['', 'この内訳は「この索引で照合を済ませた範囲」の件数。194件などの旧暫定残数との単純な減算はしない。',
              'B356/B357はround5/7の一般構成を優先し、round24の別証明を二件追加とは数えない。','',
              '## B001〜B600','', '| ID | 原文の題名・種別 | 原文監査 | 採用した証拠 |','|---|---|---|---|']
    for row in rows:
        title = row['title'].replace('|','∣')
        original = f"[{row['id']}](../{row['bank']}#L{row['original_line']})"
        evidence = f"[{row['preferred_report']}]({row['preferred_report']})" if row['preferred_report'] else f"旧個票参照{len(row['evidence_pointers'])}箇所（JSON）"
        lines.append(f"| {original} | [{row['tag']}] {title} | {row['original_status']} | {evidence} |")
    lines += ['', '再現: `python research/verification/scripts/round26_scope_index.py`。',
              '[機械可読索引](round26_original_scope_index.json)には各原文行、節の前提、根拠の種類と採用理由を含める。',
              '根拠の更新はスクリプト内の明示的なREVIEWEDへ加える。推測したステータスで空欄を埋めない。','']
    atomic_text(ROOT/'round26-original-scope-index.md','\n'.join(lines))
    print('PASS originals=600; reviewed=',reviewed_count,'audit states=',counts,'pointers=',sum(len(r['evidence_pointers']) for r in rows))


if __name__ == '__main__':
    main()
