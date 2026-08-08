# DEPTH A 全库机械 Depth Audit

评分口径：MECHANICAL_SCORE_NOT_FACT_QUALITY_JUDGMENT（仅统计内容结构，不评估事实质量）。

实体：72 | 关系：150

## Bottom 20 实体（机械分最低）

| rank | entity | score | zh | secs | src | ev | rel |
|---|---|---|---|---|---|---|---|
| 1 | person-amadou-nionson-diarra | 18 | 47 | 4 | 1 | 1 | 1 |
| 2 | person-sidi-ongoiba | 18 | 44 | 4 | 1 | 1 | 1 |
| 3 | person-ibrahim-malam-dicko | 19 | 48 | 4 | 1 | 1 | 1 |
| 4 | person-abou-ghosmane | 20 | 74 | 4 | 1 | 1 | 2 |
| 5 | person-ousmane-dicko | 20 | 61 | 4 | 1 | 1 | 2 |
| 6 | actor-katiba-serma | 21 | 66 | 4 | 1 | 1 | 4 |
| 7 | person-youssouf-toloba | 21 | 50 | 4 | 2 | 1 | 1 |
| 8 | actor-dozos-of-macina | 22 | 60 | 4 | 1 | 1 | 4 |
| 9 | actor-dana-atem | 26 | 61 | 4 | 1 | 2 | 6 |
| 10 | actor-katiba-hanifa | 32 | 74 | 4 | 3 | 2 | 6 |
| 11 | person-jafar-dicko | 37 | 107 | 5 | 2 | 2 | 3 |
| 12 | actor-niger-armed-forces | 42 | 152 | 6 | 1 | 1 | 2 |
| 13 | person-abu-hanifa | 51 | 281 | 6 | 3 | 2 | 3 |
| 14 | actor-slm-aw | 52 | 631 | 11 | 1 | 0 | 0 |
| 15 | actor-hcua | 53 | 179 | 7 | 1 | 1 | 2 |
| 16 | person-sadou-samahouna | 53 | 159 | 7 | 1 | 1 | 3 |
| 17 | actor-cameroon-bir | 54 | 564 | 11 | 1 | 1 | 0 |
| 18 | actor-ola | 55 | 600 | 11 | 1 | 1 | 1 |
| 19 | actor-vdp | 55 | 575 | 11 | 1 | 1 | 1 |
| 20 | actor-wagner-group | 55 | 195 | 7 | 1 | 1 | 4 |

## Bottom 20 关系（机械分最低）

| rank | relation | score | zh | tl | src | ev |
|---|---|---|---|---|---|---|
| 1 | rel-ssudan-sudan-spillover | 2 | 0 | 0 | 1 | 0 |
| 2 | rel-is-moz-tanzania-link | 2 | 0 | 0 | 1 | 0 |
| 3 | rel-fadm-mozambique-operates | 2 | 0 | 0 | 1 | 0 |
| 4 | rel-d1-fla-mali-operates | 2 | 0 | 0 | 1 | 0 |
| 5 | rel-d1-fla-fama-conflict | 2 | 0 | 0 | 1 | 0 |
| 6 | rel-d1-wagner-fama-coop | 2 | 0 | 0 | 1 | 0 |
| 7 | rel-d1-wagner-jnim-conflict | 2 | 0 | 0 | 1 | 0 |
| 8 | rel-d1-ansarul-burkina-operates | 2 | 0 | 0 | 1 | 0 |
| 9 | rel-d1-abu-hanifa-niger | 2 | 0 | 0 | 1 | 0 |
| 10 | rel-d1-sadou-burkina-history | 2 | 0 | 0 | 1 | 0 |
| 11 | rel-d1-niger-army-niger | 2 | 0 | 0 | 1 | 0 |
| 12 | rel-d1-ansaru-jas-split | 2 | 0 | 0 | 1 | 0 |
| 13 | rel-d1-lakurawa-nigeria-operates | 2 | 0 | 0 | 1 | 0 |
| 14 | rel-d1-lakurawa-niger-operates | 2 | 0 | 0 | 1 | 0 |
| 15 | rel-d1-dan-na-mali-operates | 2 | 0 | 0 | 1 | 0 |
| 16 | rel-d2-ousmane-burkina | 2 | 0 | 0 | 1 | 0 |
| 17 | rel-d2-katiba-hanifa-niger | 2 | 0 | 0 | 1 | 0 |
| 18 | rel-d2-katiba-hanifa-burkina | 2 | 0 | 0 | 1 | 0 |
| 19 | rel-d2-katiba-serma-mali | 2 | 0 | 0 | 1 | 0 |
| 20 | rel-d2-katiba-serma-burkina | 2 | 0 | 0 | 1 | 0 |

## E3/R3 候选（本轮 packet 升级目标）

实体:

- actor-wagner-group: score=55 zh=195 secs=7
- person-amadou-koufa: score=62 zh=546 secs=9
- actor-ansarul-islam: score=62 zh=333 secs=7
- actor-africa-corps: score=63 zh=304 secs=8
- actor-al-mourabitoun: score=68 zh=989 secs=15
- person-iyad-ag-ghali: score=68 zh=455 secs=9
- actor-katiba-macina: score=70 zh=1077 secs=15
- actor-aqim: score=70 zh=977 secs=15
- actor-fla: score=70 zh=396 secs=8
- actor-is-sahel: score=80 zh=1014 secs=15
- actor-jnim: score=85 zh=1424 secs=17

关系:

- rel-koufa-katiba-founder: score=4 zh=0 tl=0
- rel-koufa-jnim-senior: score=4 zh=0 tl=0
- rel-jnim-aqim-constituent: score=6 zh=0 tl=0
- rel-jnim-katiba-constituent: score=6 zh=0 tl=0
- rel-jnim-iyad-led: score=8 zh=0 tl=0
- rel-d1-ansarul-jnim-constituent: score=21 zh=52 tl=2
- rel-d1-africa-corps-wagner-history: score=21 zh=39 tl=2
- rel-jnim-is-conflict: score=25 zh=62 tl=2
- rel-d1-fla-jnim-cooperation: score=25 zh=62 tl=3
- rel-d1-africa-corps-fama-coop: score=25 zh=41 tl=3
- rel-jnim-alqaida-affiliate: score=43 zh=404 tl=3