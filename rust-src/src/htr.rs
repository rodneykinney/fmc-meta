use crate::solver::{solve_step, solve_step_deduplicated, step_config};
use crate::{
    Algorithm, DrawableCorner, Solvable, CORNER_FB_FACELETS, CORNER_RL_FACELETS,
    CORNER_UD_FACELETS, EDGE_FB_FACELETS, EDGE_RL_FACELETS, EDGE_UD_FACELETS,
};
use cubelib::cube::turn::ApplyAlgorithm;
use cubelib::cube::{Cube333, Direction, Turn333};
use cubelib::defs::StepKind;
use cubelib::steps::fr::coords::{FRUDNoSliceCoord};
use cubelib::steps::coord::Coord;
use pyo3::exceptions::PyValueError;
use pyo3::PyResult;
use std::str::FromStr;

pub struct HTRUD;
impl Solvable for HTRUD {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        let turn = Turn333::from_str(s).map_err(|_| PyValueError::new_err("Invalid move"))?;
        Ok(turn.dir == Direction::Half)
    }
    fn is_solved(&self, cube: &Cube333) -> bool {
        match cube.get_dr_subset() {
            Some(s) => s.qt == 0,
            _ => false,
        }
    }
    fn is_eligible(&self, cube: &Cube333) -> bool {
        match cube.get_dr_subset() {
            Some(_) => true,
            _ => false,
        }
    }
    fn case_name(&self, cube: &Cube333) -> String {
        match cube.get_dr_subset() {
            Some(s) => s.to_string(),
            _ => "".to_string(),
        }
    }
    fn should_draw_edge(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let e = cube.edges.get_edges()[pos];
        !e.oriented_ud && Some(facelet) != EDGE_UD_FACELETS[pos]
    }
    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        (c.id / 4 == 1 && facelet == c.facelet_showing_ud()) || // D sticker
            (!c.oriented_fb(pos as u8) && facelet != CORNER_UD_FACELETS[pos])
    }
    fn solve(&self, cube: &Cube333, max: u8) -> PyResult<Vec<Algorithm>> {
        let unique_fn = |alg: &Algorithm| {
            let mut c = cube.clone();
            c.apply_alg(&alg.0);
            let coord1 = FRUDNoSliceCoord::from(&c);
            c.apply_alg(&Algorithm::new("U2 D2").unwrap().0);
            let coord2 = FRUDNoSliceCoord::from(&c);
            std::cmp::min(coord1.val(), coord2.val())
        };
        let algs = solve_step_deduplicated(cube, step_config(StepKind::HTR, "", Some(max)), 100, true, unique_fn)
            .map_err(|e| PyValueError::new_err(e))?;
        // let algs = solve_step(cube, step_config(StepKind::HTR, "", Some(max)), 100, true)
        //     .map_err(|e| PyValueError::new_err(e))?;
        Ok(algs)
    }
}
pub struct HTRFB;
impl Solvable for HTRFB {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        HTRUD.is_move_allowed(s)
    }
    fn is_solved(&self, cube: &Cube333) -> bool {
        HTRUD.is_solved(cube)
    }
    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRUD.is_eligible(cube)
    }
    fn case_name(&self, cube: &Cube333) -> String {
        HTRUD.case_name(cube)
    }
    fn should_draw_edge(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let e = cube.edges.get_edges()[pos];
        !e.oriented_fb && Some(facelet) != EDGE_FB_FACELETS[pos]
    }
    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        (vec!(0, 1, 6, 7).contains(&c.id) && facelet == c.facelet_showing_fb()) || // B sticker
            (!c.oriented_rl(pos as u8) && facelet != CORNER_FB_FACELETS[pos])
    }
    fn solve(&self, cube: &Cube333, max: u8) -> PyResult<Vec<Algorithm>> {
        let algs = solve_step(cube, step_config(StepKind::HTR, "", Some(max)), 100, true)
            .map_err(|e| PyValueError::new_err(e))?;
        Ok(algs)
    }
}
pub struct HTRRL;
impl Solvable for HTRRL {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        HTRUD.is_move_allowed(s)
    }
    fn is_solved(&self, cube: &Cube333) -> bool {
        HTRUD.is_solved(cube)
    }
    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRUD.is_eligible(cube)
    }
    fn case_name(&self, cube: &Cube333) -> String {
        HTRUD.case_name(cube)
    }
    fn should_draw_edge(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let e = cube.edges.get_edges()[pos];
        !e.oriented_rl && Some(facelet) != EDGE_RL_FACELETS[pos]
    }
    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        (vec!(1, 2, 5, 6).contains(&c.id) && facelet == c.facelet_showing_rl()) || // L sticker
            (!c.oriented_ud(pos as u8) && facelet != CORNER_RL_FACELETS[pos])
    }
    fn solve(&self, cube: &Cube333, max: u8) -> PyResult<Vec<Algorithm>> {
        let algs = solve_step(cube, step_config(StepKind::HTR, "", Some(max)), 100, true)
            .map_err(|e| PyValueError::new_err(e))?;
        Ok(algs)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use cubelib::algs::Algorithm as LibAlgorithm;

    #[test]
    fn test_unique_htr() {
        let mut cube = Cube333::default();
        cube.apply_alg(&LibAlgorithm::from_str("U2 F2").unwrap());
        let coord_1 = FRUDNoSliceCoord::from(&cube);
        let mut cube2 = Cube333::default();
        cube2.apply_alg(&LibAlgorithm::from_str("U D R2 U D'").unwrap());
        let coord_2 = FRUDNoSliceCoord::from(&cube2);
        assert_eq!(coord_1, coord_2);
    }

    #[test]
    fn test_find() {
        let scramble = "F' R F R B R2 D R2 B' D F' L2 D2 L2 B' L2 B R2 D2 F2 U2 L2 B2 R2 U' F' U' L D' L";
        let mut cube = Cube333::default();
        cube.apply_alg(&LibAlgorithm::from_str(scramble).unwrap());
        let algs = HTRUD.solve(&cube, 100).unwrap();
        assert_ne!(algs.len(), 0);
    }
}