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
  EO: All EOs up to 5 moves. Allow up to 1 pre-moves. Choose 30 for DR attempt
  DR: Optimal DR, without breaking EO, up to 12 moves, including EO. Choose 10 for finish attempt
  Finish: Optimal finish without breaking DR
single-axis-dr:
  EO: All EOs up to 5 moves. Allow up to 1 pre-moves. Choose 30 for DR attempt
  DR: Intuitively findable DRs (pure rzp or jzp), up to 14 moves, including EO. Choose 10 for finish attempt
  Finish: Optimal finish without breaking DR
easy-corners:
  EO: All EOs up to 5 moves. Allow up to 1 pre-moves. Choose 30 for DR attempt
  DR: Intuitively findable DRs (pure rzp or jzp), up to 14 moves, including EO. Choose 10 for finish attempt
  Finish: Optimal finish with <= 3 QTs, not breaking DR

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
```

This session looks at the effect of abandoning any DR finish requiring more than 3 quarter turns. 
The `easy-corners` meta considers only 3qt DR finishes to be findable, resulting in a 23. 
The `single-axis-dr` considers any DR finish to be findable, and gets a 21.

However, one could argue that only looking at 3QT DRs allows one to check more finishes. 
What if we increase the number of DRs retained?

```
$ fmc-meta solve --meta easy-corners --dr.retain=20 "R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2"
Using meta=easy-corners
Scramble: R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2
Looking for EOs
Found EOs: 1x3-moves 10x4-moves 153x5-moves
Looking for DRs on 30 EOs: 1x3-moves 10x4-moves 19x5-moves
Found DRs: 1x10-moves 7x11-moves 90x12-moves 672x13-moves 4256x14-moves
Looking for finishes on 20 DRs: 1x10-moves 7x11-moves 12x12-moves

(B' F' U2 D2 L) // eorl (5)
(D L2 B2 D' R2 B) // drud-eorl (11)
R2 L2 B2 U F2 D R2 U2 F2 B2 R2 U' B2 // drudfin (23)
```

Still only a 23. What if we increase even more?

```
$ fmc-meta solve --meta easy-corners --dr.retain=30 "R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2"
Using meta=easy-corners
Scramble: R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2
Looking for EOs
Found EOs: 1x3-moves 10x4-moves 153x5-moves
Looking for DRs on 30 EOs: 1x3-moves 10x4-moves 19x5-moves
Found DRs: 1x10-moves 7x11-moves 90x12-moves 672x13-moves 4256x14-moves
Looking for finishes on 30 DRs: 1x10-moves 7x11-moves 22x12-moves

L (F D R) // eorl (4)
(U' R2 D' F2 U D L2 F) // drud-eorl (12)
D L2 F2 L2 B2 D' F2 B2 R2 D2 F2 // drudfin (22)
```

After increasing to 30 DRs retained, we finally get a 22. 
