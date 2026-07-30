# Deep geometry audit, PHercParis4 spiral-input verified patches

Patches inspected: **5210** (1 failed to load). Split: 4917 ordinary patches, 293 band/backup surfaces (long multi-winding strips).

Validity follows VC3D's loader (`z<=0`, `mask.tif` channel 0 `<255`, and `x==-1` all invalidate), see the README. Numbers below were regenerated after that correction.

**Suspect verification.** We hand-checked the top flagged patches in both groups. Band surfaces: suspect pairs sit at median 8.9-voxel 3D distance across ~309-cell UV separation, legitimate adjacent-winding clearance, not duplicated geometry. Top ordinary patches (elongated strips): pairs at 6-9 voxels across 121-243 cells UV, zero near-duplicate (<1 voxel) pairs, consistent with tight winding rather than confirmed sheet switches. In a human-verified corpus this is the expected outcome; the flag's value is marking close-approach zones where automatic mesh growth risks jumping sheets, and in screening *unverified* auto-grown patches. These are heuristic cues, not a validated sheet-switch detector, for rigorous evaluation of that specific problem see aviad12g/tifxyz-doctor's sealed-holdout benchmark and joe-carr-data/windcheck's self-intersection certificates.

## Ordinary patches

- with sheet-switch/merger suspects: **42**
- with interior holes: **615**
- with >1% stretched edges: **510**
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

## Band/backup surfaces (self-proximity expected)

- flagged: 31 of 293; holes: 55

