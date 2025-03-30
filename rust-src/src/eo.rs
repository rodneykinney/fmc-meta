use crate::{Algorithm, Solvable};
use crate::solver::{solve_step, step_config};
use cubelib::cube::{Cube333, CubeFace, Direction, Turn333};
use cubelib::steps::eo::coords::BadEdgeCount;
use pyo3::exceptions::PyValueError;
use pyo3::PyResult;
use std::str::FromStr;
use cubelib::defs::StepKind;

pub struct EOUD;
impl Solvable for EOUD {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        let turn = Turn333::from_str(s).map_err(|_| PyValueError::new_err("Invalid move"))?;
        match turn.face {
            CubeFace::Up | CubeFace::Down => Ok(turn.dir == Direction::Half),
            _ => Ok(true),
        }
    }
    fn is_solved(&self, cube: &Cube333) -> bool {
        cube.count_bad_edges_ud() == 0
    }

    fn is_eligible(&self, _cube: &Cube333) -> bool {
        true
    }
    fn case_name(&self, cube: &Cube333) -> String {
        format!("{}e", cube.count_bad_edges_ud())
    }
    fn should_draw_edge(&self, cube: &Cube333, pos: usize, _facelet: u8) -> bool {
        !cube.edges.get_edges()[pos].oriented_ud
    }
    fn should_draw_corner(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        false
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::EO, "ud"), count, true)
    }
}
pub struct EOFB;
impl Solvable for EOFB {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        let turn = Turn333::from_str(s).map_err(|_| PyValueError::new_err("Invalid move"))?;
        match turn.face {
            CubeFace::Front | CubeFace::Back => Ok(turn.dir == Direction::Half),
            _ => Ok(true),
        }
    }

    fn is_solved(&self, cube: &Cube333) -> bool {
        cube.count_bad_edges_fb() == 0
    }

    fn is_eligible(&self, _cube: &Cube333) -> bool {
        true
    }
    fn case_name(&self, cube: &Cube333) -> String {
        format!("{}e", cube.count_bad_edges_fb())
    }
    fn should_draw_edge(&self, cube: &Cube333, pos: usize, _facelet: u8) -> bool {
        !cube.edges.get_edges()[pos].oriented_fb
    }
    fn should_draw_corner(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        false
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
      solve_step(cube, step_config(StepKind::EO, "fb"), count, true)
    }
}
pub struct EORL;
impl Solvable for EORL {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        let turn = Turn333::from_str(s).map_err(|_| PyValueError::new_err("Invalid move"))?;
        match turn.face {
            CubeFace::Right | CubeFace::Left => Ok(turn.dir == Direction::Half),
            _ => Ok(true),
        }
    }

    fn is_solved(&self, cube: &Cube333) -> bool {
        cube.count_bad_edges_lr() == 0
    }

    fn is_eligible(&self, _cube: &Cube333) -> bool {
        true
    }
    fn case_name(&self, cube: &Cube333) -> String {
        format!("{}e", cube.count_bad_edges_lr())
    }
    fn should_draw_edge(&self, cube: &Cube333, pos: usize, _facelet: u8) -> bool {
        !cube.edges.get_edges()[pos].oriented_rl
    }
    fn should_draw_corner(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        false
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::EO, "lr"), count, true)
    }
}
