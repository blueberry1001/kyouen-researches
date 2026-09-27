# 6x6 T* / WFT exact result

Complete evaluation of 5,081,289 reachable safe positions gives:

- `T*(empty) = {7,9,11}`
- `WFT(empty) = {9}`
- all 36 one-stone positions have `g=0`, `T*={7,9,11}`, `WFT={9}`
- forbidden quadruples: 2,491

Consequences: the known maximum safe-set size `K_6=11` is reachable along an outcome-preserving line, so n=6 does not provide the hoped-for B034 witness. B040 is supported through n=6; although three terminal lengths are possible along outcome-preserving play, the winner can force exactly 9 stones against every response.

Machine-readable evidence: `research/verification/data/n6_tstar_wft_exact.json`.
