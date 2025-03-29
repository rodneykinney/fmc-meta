use crate::eo::{EOFB, EORL, EOUD};
use crate::solver::{solve_step, step_config};
use crate::{Algorithm, DrawableCorner, Solvable};
use cubelib::cube::turn::TransformableMut;
use cubelib::cube::{Corner, Cube333, CubeFace, Direction, Transformation333, Turn333};
use cubelib::steps::coord::Coord;
use cubelib::steps::dr::coords::DRUDEOFBCoord;
use cubelib::steps::eo::coords::BadEdgeCount;
use pyo3::exceptions::PyValueError;
use pyo3::PyResult;
use std::str::FromStr;
use cubelib::defs::StepKind;

pub struct DRUD;
impl Solvable for DRUD {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        let turn = Turn333::from_str(s).map_err(|_| PyValueError::new_err("Invalid move"))?;
        match turn.face {
            CubeFace::Up | CubeFace::Down => Ok(true),
            _ => Ok(turn.dir == Direction::Half),
        }
    }

    fn is_solved(&self, cube: &Cube333) -> bool {
        let solved = cube.count_bad_edges_fb() == 0
            && cube.count_bad_edges_lr() == 0
            && DRUDEOFBCoord::from(cube).val() == 0;
        solved
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        EORL.is_solved(cube) || EOFB.is_solved(cube)
    }
    fn case_name(&self, cube: &Cube333) -> String {
        let bad_corner_count = cube
            .corners
            .get_corners()
            .into_iter()
            .filter(|c: &Corner| c.orientation != 0)
            .count();
        let bad_edge_count = cube.count_bad_edges_lr() + cube.count_bad_edges_fb();
        format!("{}c{}e", bad_corner_count, bad_edge_count)
    }
    fn should_draw_edge(&self, cube: &Cube333, pos: usize, _facelet: u8) -> bool {
        let e = cube.edges.get_edges()[pos];
        !e.oriented_fb || !e.oriented_rl
    }
    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        !c.oriented_ud(pos as u8) && facelet == c.facelet_showing_ud()
    }
    fn solve(&self, cube: &Cube333, max: u8) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::DR, "ud", Some(max)), 100, true).map_err(|e| PyValueError::new_err(e))
    }
}

pub struct DRFB;
impl Solvable for DRFB {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        let turn = Turn333::from_str(s).map_err(|_| PyValueError::new_err("Invalid move"))?;
        match turn.face {
            CubeFace::Front | CubeFace::Back => Ok(true),
            _ => Ok(turn.dir == Direction::Half),
        }
    }

    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::X);
        DRUD.is_solved(&cube)
    }
    fn is_eligible(&self, cube: &Cube333) -> bool {
        EORL.is_solved(cube) || EOUD.is_solved(cube)
    }
    fn case_name(&self, cube: &Cube333) -> String {
        let mut cube = cube.clone();
        cube.transform(Transformation333::X);
        DRUD.case_name(&cube)
    }
    fn should_draw_edge(&self, cube: &Cube333, pos: usize, _facelet: u8) -> bool {
        let e = cube.edges.get_edges()[pos];
        !e.oriented_ud || !e.oriented_rl
    }
    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        !c.oriented_fb(pos as u8) && facelet == c.facelet_showing_fb()
    }
    fn solve(&self, cube: &Cube333, max: u8) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::DR, "fb", Some(max)), 100, true).map_err(|e| PyValueError::new_err(e))
    }
}
pub struct DRRL;
impl Solvable for DRRL {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        let turn = Turn333::from_str(s).map_err(|_| PyValueError::new_err("Invalid move"))?;
        match turn.face {
            CubeFace::Right | CubeFace::Left => Ok(true),
            _ => Ok(turn.dir == Direction::Half),
        }
    }
    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Z);
        DRUD.is_solved(&cube)
    }
    fn is_eligible(&self, cube: &Cube333) -> bool {
        EOUD.is_solved(cube) || EOFB.is_solved(cube)
    }
    fn case_name(&self, cube: &Cube333) -> String {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Z);
        DRUD.case_name(&cube)
    }
    fn should_draw_edge(&self, cube: &Cube333, pos: usize, _facelet: u8) -> bool {
        let e = cube.edges.get_edges()[pos];
        !e.oriented_fb || !e.oriented_ud
    }
    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        !c.oriented_rl(pos as u8) && facelet == c.facelet_showing_rl()
    }
    fn solve(&self, cube: &Cube333, max: u8) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::DR, "lr", Some(max)), 100, true).map_err(|e| PyValueError::new_err(e))
    }
}
