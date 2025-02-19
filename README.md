# fmc-meta

`fmc-meta` is a human-fmc-attempt simulator. It uses [nissy](https://nissy.tronto.net/) to execute the stages of a standard EO-DR-Finish strategy on a given scramble. However, `nissy` will only consider EOs/DRs/Finishes that you consider "findable", which you specify on the command line. The output is a list of annotated solutions.

How good is your FMC "meta"? Should you focus on NISS-ing your short EOs or searching for DRs on longer EOs? Should you learn to recognize EO-breaking DRs? Should you learn to solve 5qt DR cases or focus on generating more low-qt DRs?  `fmc-meta` aims to answer these questions.

## Installation

Install [nissy](https://nissy.tronto.net/) so that `which nissy` runs successfully.

Install `fmc-meta` from a clone of this repo:
```
pip install -e .
```

## Usage

A sample session is shown below:
```
$ fmc-meta list
Available metas:

near-optimal:
  EOs: include NISS. DRs: optimal. Finishes: optimal
single-axis-dr:
  EOs: include NISS. DRs: only pure rzp or jzp. Finishes: optimal
debug:
  For debugging
easy-corners:
  EOs: include NISS. DRs: only pure rzp or jzp. Finishes: easy corners only

$ fmc-meta show-options easy-corners
Config options for easy-corners:
  --eo.max_eo_length=5
    Maximum move count
  --eo.retain=30
    Attempt to find DR on this many EOs
  --eo.check_inverse=True
    Check both normal and inverse
  --eo.max_niss_split=1
    Maximum number of moves before NISS
  --eo.seed=None
    Random seed

  --dr.max_dr_length=12
    Maximum move count
  --dr.retain=10
    Attempt to finish this many DRs
  --dr.check_inverse=True
    Check both normal and inverse
  --dr.seed=None
    Random seed

  --finish.max_qt_count=3
    Don't attempt DR cases with more than this many QTs

$ fmc-meta solve --meta easy-corners "R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2"
Using meta=easy-corners
Scramble: R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2
Looking for EOs
Found EOs: 1x3-moves 10x4-moves 153x5-moves
Looking for DRs on 30 EOs: 1x3-moves 10x4-moves 19x5-moves
Found DRs: 1x10-moves 7x11-moves 76x12-moves
Looking for finishes on 10 DRs: 1x10-moves 7x11-moves 2x12-moves

(B' F' U2 D2 L) // eorl (5)
(D L2 B2 D' R2 B) // drud-eorl (11)
R2 L2 B2 U F2 D R2 U2 F2 B2 R2 U' B2 // drudfin (23)

(B' F' U2 D2 L) // eorl (5)
(D F2 U L2 B) // drud-eorl (10)
D2 L2 D2 B2 D' L2 B2 D' L2 B2 D' F2 U2 F2 // drudfin (24)

U' F' L (R) // eorl (4)
(R2 U2 B' D2 B L2 F' D) // drfb-eorl (11)
R2 L2 B' R2 U2 F R2 F2 D2 U2 L2 D2 B // drfbfin (24)

$ fmc-meta solve --meta single-axis-dr "R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2"
Using meta=single-axis-dr
Scramble: R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2
Looking for EOs
Found EOs: 1x3-moves 10x4-moves 153x5-moves
Looking for DRs on 30 EOs: 1x3-moves 10x4-moves 19x5-moves
Found DRs: 1x10-moves 7x11-moves 76x12-moves
Looking for finishes on 10 DRs: 1x10-moves 7x11-moves 2x12-moves

L (F D R) // eorl (4)
U2 B2 L2 U R2 U F // drud-eorl (11)
D' R2 B2 U2 D' R2 B2 D' B2 D' // drudfin (21)

(B' F' U2 D2 L) // eorl (5)
(D F2 U L2 B) // drud-eorl (10)
F2 D B2 L2 U L2 U L2 U L2 D' F2 D2 B2 // drudfin (23)

(B' F' U2 D2 L) // eorl (5)
(D L2 B2 D' R2 B) // drud-eorl (11)
R2 L2 B2 U F2 D R2 U2 F2 B2 R2 U' B2 // drudfin (23)
```

This session looks at the effect of abandoning any DR finish requiring more than 3 quarter turns. 
The `easy-corners` meta considers only 3qt DR finishes to be findable, resulting in a 23. 
The `single-axis-dr` considers any DR finishes findable, and gets a 21.
