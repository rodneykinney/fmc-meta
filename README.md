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
  near-optimal
  single-axis-dr
  debug
  easy-corners

$ fmc-meta --show --meta easy-corners
Behavior of --meta easy-corners:

EO:
Find all EOs up to 5 moves
Check normal and inverse
Maximum NISS split: 1
Keep the 30 shortest EOs
Prefer non-NISS


DR:
Find all DRs up to 12 moves, including the preceding EO
Don't break EO.
Check normal and inverse
Don't NISS in the middle
Keep the 10 shortest DRs
Prefer non-NISS

Finish:
Find the optimal DR solution that doesn't break DR
Give up unless DR is 3QT or less


$ fmc-meta --meta easy-corners "R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2"
Using meta=easy-corners
Scramble: R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2
Looking for EOs
Found EOs: 1x3-moves 10x4-moves 153x5-moves
Looking for DRs on 30 EOs: 1x3-moves 10x4-moves 19x5-moves
Found DRs: 10x10-moves 71x11-moves 885x12-moves
Looking for finishes on 10 DRs: 10x10-moves

(B F R) // eorl (3)
(F L2 B' R2 U B F) // drud-eorl (10)
L2 F2 R2 L2 U' B2 L2 U' F2 R2 U L2 U2 R2 // drudfin (24)


$ fmc-meta --meta near-optimal "R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2"
Using meta=near-optimal
Scramble: R U' F2 R2 D' R F' B' R F B2 D R2 U' F2 U B2 D L2 B2 D L2 F2
Looking for EOs
Found EOs: 1x3-moves 10x4-moves 153x5-moves
Looking for DRs on 30 EOs: 1x3-moves 10x4-moves 19x5-moves
Found DRs: 8x10-moves 61x11-moves 861x12-moves
Looking for finishes on 10 DRs: 8x10-moves 2x11-moves

(B F R) // eorl (3)
F D B2 D' F U2 B // drud-eorl (10)
U B2 D' L2 U L2 D' R2 U' F2 D2 R2 // drudfin (22)

U' F' L (R) // eorl (4)
(U' F2 L2 F' D' F' U) // drfb-eorl (11)
F B2 D2 R2 B' L2 D2 B' L2 D2 B D2 // drfbfin (23)

L (F D R) // eorl (4)
L2 U B' D' F' D // drfb-eorl (10)
D2 F' D2 L2 B U2 B' R2 U2 B' L2 F D2 B' // drfbfin (24)
```

In this session, we look at the effect of abandoning any DR finish requiring more than 3 quarter turns. The meta that considers only 3qt DR finishes finds a 24 with no backup solutions. The meta that finishes any DR finds a 22 from the same EO. There is some randomness because both metas are able to check all 4-move EOs but have to choose randomly from the available 5-move EOs. For that reason, the near-optimal meta finds only 8 10-move DRs compared to the 10 found by the easy-corners meta.