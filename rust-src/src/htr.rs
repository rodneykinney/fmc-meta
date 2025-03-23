use std::str::FromStr;
use cubelib::cube::{Cube333, Direction, Turn333};
use pyo3::exceptions::PyValueError;
use pyo3::PyResult;
use crate::{DrawableCorner, Solvable, CORNER_FB_FACELETS, CORNER_RL_FACELETS, CORNER_UD_FACELETS, EDGE_FB_FACELETS, EDGE_RL_FACELETS, EDGE_UD_FACELETS};

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
}
