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
$ fmc-meta --list
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
  --finish.max_length=15
    Maximum move count

$ fmc-meta --meta easy-corners "R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2"
Using meta=easy-corners
Scramble: R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2
Looking for EOs
Found EOs: 1x3-moves 10x4-moves 153x5-moves
Looking for DRs on 30 EOs: 1x3-moves 10x4-moves 19x5-moves
Found DRs: 2x9-moves 6x10-moves 90x11-moves 826x12-moves
Looking for finishes on 10 DRs: 2x9-moves 6x10-moves 2x11-moves

(B F R) // eorl (3)
(F L2 B' R2 U B F) // drud-eorl (10)
B2 U R2 B2 L2 F2 L2 D' L2 U' B2 U2 R2 F2 // drudfin (24)

$ fmc-meta --meta near-optimal "R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2"
Using meta=near-optimal
Scramble: R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2
Looking for EOs
Found EOs: 1x3-moves 10x4-moves 153x5-moves
Looking for DRs on 30 EOs: 1x3-moves 10x4-moves 19x5-moves
Found DRs: 2x9-moves 8x10-moves 100x11-moves 818x12-moves
Looking for finishes on 10 DRs: 2x9-moves 8x10-moves

L (F D R) // eorl (4)
L2 U B' D' F' D // drfb-eorl (9)
D2 F' D2 L2 B U2 B' R2 U2 B' L2 F D2 B' // drfbfin (22)

(B F R) // eorl (3)
F D B2 D' F U2 B // drud-eorl (10)
U B2 D' L2 U L2 D' R2 U' F2 D2 R2 // drudfin (22)

(B F R) // eorl (3)
F D B2 D' B L2 F // drud-eorl (10)
F2 U' R2 D B2 D' F2 R2 U R2 D2 B2 L2 D' // drudfin (23)
```

This session looks at the effect of abandoning any DR finish requiring more than 3 quarter turns. 
The meta that considers only 3qt DR finishes finds a 24 with no backup solutions. 
The meta that finishes any DR finds a 22 from the same EO. 
There is some randomness because both metas are able to check all 4-move EOs 
but have to choose randomly from the available 5-move EOs.