# Deep geometry audit — PHercParis4 spiral-input verified patches

Patches inspected: **5210** (1 failed to load). Split: 4917 ordinary patches, 293 band/backup surfaces (long multi-winding strips).

**Interpretation note.** The `self_proximity` metric flags grid-distant vertex pairs that come close in 3D. For *ordinary local patches* this is a sheet-switch/merger red flag. For *band surfaces* that legitimately wrap around the scroll, adjacent windings naturally pass within a few voxels of each other — we verified the flagged band pairs sit at median 8.9-voxel distance with ~309-cell UV separation and are NOT duplicated geometry. Band-surface flags below are therefore expected geometry, reported separately; they double as a measurement of local winding clearance (min observed: 0.7 voxels).

## Ordinary patches

- with sheet-switch/merger suspects: **44**
- with interior holes: **620**
- with >1% stretched edges (>1.5x expected spacing): **510**
- with >5% normal flips: **18**

### Top sheet-switch suspects (ordinary patches)

| suspect pairs | cells | patch |
|---|---|---|
| 555 | 1075 | `auto_grown_20260429215626691_sel_20260512_102916_79` |
| 482 | 956 | `auto_grown_20260429215626691_sel_20260512_102916_1` |
| 430 | 856 | `auto_grown_20260429220809522_sel_20260512_104236_40` |
| 417 | 823 | `auto_grown_20260429215626691_sel_20260512_102916_57` |
| 303 | 605 | `5753_-1_flatboi_copy` |
| 233 | 466 | `auto_grown_20260429203853823_sel_20260512_103415_18` |
| 205 | 410 | `auto_grown_20260429215626691_sel_20260512_102916_63` |
| 163 | 325 | `auto_grown_20260429203853823_sel_20260512_103415_15` |
| 144 | 288 | `auto_grown_20260429215626691_sel_20260512_102916_30` |
| 115 | 230 | `4424_david_masked` |
| 61 | 122 | `auto_grown_20260429203853823_sel_20260512_103415_40` |
| 52 | 104 | `auto_grown_20260526104703844_flatboi_sel_20260526_113725_10` |
| 52 | 101 | `auto_grown_20260526112529933_sel_20260526_113228_49` |
| 50 | 100 | `auto_grown_20260526104703844_flatboi_sel_20260526_113725_1` |
| 42 | 84 | `auto_grown_20260526112529933_sel_20260526_113228_32` |

### Largest interior holes (ordinary patches)

| holes | total cells | largest | patch |
|---|---|---|---|
| 4 | 18116 | 12571 | `4424_david_masked` |
| 10 | 8301 | 2810 | `5753_-1_flatboi_copy` |
| 8 | 1145 | 225 | `auto_grown_20260429215626691_sel_20260512_102916_79` |
| 1 | 1015 | 1015 | `auto_grown_20260416054404425` |
| 2 | 871 | 869 | `fill_0007_sel_20260512_111459_2` |
| 11 | 867 | 838 | `auto_grown_20260420221357203` |
| 5 | 783 | 656 | `auto_grown_20260429203853823_sel_20260512_103415_26` |
| 1 | 707 | 707 | `auto_grown_20260427203309936_region_001` |
| 1 | 613 | 613 | `auto_grown_20260415195829414` |
| 2 | 589 | 384 | `middle_3_flat` |
| 2 | 538 | 454 | `auto_grown_20260427203229840` |
| 3 | 525 | 425 | `auto_grown_20260526104703844_flatboi_sel_20260526_113725_6` |
| 1 | 490 | 490 | `auto_grown_20260415173749401` |
| 8 | 479 | 153 | `auto_grown_20260526104703844_flatboi_sel_20260526_113725_1` |
| 1 | 419 | 419 | `auto_grown_20260415210510251` |

### Worst stretch (ordinary patches)

| stretched edge frac | median spacing | patch |
|---|---|---|
| 37.2% | 23.1 | `auto_grown_20260526205436971_sel_20260526_212050_80` |
| 36.9% | 24.7 | `auto_grown_20260526200530340_sel_20260526_211217_75` |
| 33.8% | 24.5 | `auto_trace_20260526151328050_sel_20260526_155150_37` |
| 32.6% | 19.5 | `auto_grown_20260526200530340_sel_20260526_211217_113` |
| 26.7% | 24.0 | `auto_grown_20260527134144893_sel_20260527_150051_22` |
| 26.0% | 26.4 | `auto_grown_20260429220809522_sel_20260512_104236_31` |
| 24.4% | 22.5 | `auto_grown_20260527134144893_sel_20260527_150051_156` |
| 23.3% | 21.2 | `auto_grown_20260526205436971_sel_20260526_212050_51` |
| 22.9% | 21.5 | `auto_grown_20260526195309752_sel_20260526_210343_42` |
| 21.4% | 22.0 | `auto_grown_20260526200530340_sel_20260526_211217_92` |

## Band/backup surfaces (self-proximity expected)

- flagged: 31 of 293; holes: 55

