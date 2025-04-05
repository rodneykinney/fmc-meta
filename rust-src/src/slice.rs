use crate::fr::{FRFB, FRRL, FRUD};
use crate::solver::{solve_step, step_config};
use crate::{Algorithm, Solvable};
use cubelib::cube::turn::TransformableMut;
use cubelib::cube::{Cube333, Transformation333};
use cubelib::defs::StepKind;
use cubelib::steps::coord::Coord;
use cubelib::steps::finish::coords::HTRLeaveSliceFinishCoord;
use pyo3::PyResult;

pub struct SliceUD;
impl Solvable for SliceUD {
    fn is_move_allowed(&self, _s: &str) -> PyResult<bool> {
        Ok(false)
    }

    fn is_solved(&self, cube: &Cube333) -> bool {
        HTRLeaveSliceFinishCoord::from(cube).val() == 0
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        FRUD.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let mut bad_edge_count = 0;
        let mut bad_corner_count = 0;
        let edges = cube.edges.get_edges();
        let corners = cube.corners.get_corners();
        for i in 0..12 {
            if edges[i].id as usize != i{
                bad_edge_count += 1;
            }
        }
        for i in 0..8 {
            if corners[i].id as usize != i {
                bad_corner_count += 1;
            }
        }
        format!("{}c{}e", bad_corner_count, bad_edge_count).to_string()
    }

    fn should_draw_edge(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        true
        // let e = cube.edges.get_edges()[pos];
        // e.id != pos as u8
    }

    fn should_draw_corner(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        true
        // let c = cube.corners.get_corners()[pos];
        // c.id != pos as u8
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::FINLS, ""), count, false)
    }
}
pub struct SliceFB;
impl Solvable for SliceFB {
    fn is_move_allowed(&self, _s: &str) -> PyResult<bool> {
        Ok(false)
    }

    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::X);
        SliceUD.is_solved(&cube)
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        FRFB.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let mut cube = cube.clone();
        cube.transform(Transformation333::X);
        SliceUD.case_name(&cube)
    }

    fn should_draw_edge(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        // let e = cube.edges.get_edges()[pos];
        // e.id != pos as u8
        true
    }

    fn should_draw_corner(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        // let c = cube.corners.get_corners()[pos];
        // c.id != pos as u8
        true
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::FINLS, ""), count, false)
    }
}

pub struct SliceRL;
impl Solvable for SliceRL {
    fn is_move_allowed(&self, _s: &str) -> PyResult<bool> {
        Ok(false)
    }

    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Z);
        SliceUD.is_solved(&cube)
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        FRRL.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Z);
        SliceUD.case_name(&cube)
    }

    fn should_draw_edge(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        // let e = cube.edges.get_edges()[pos];
        // e.id != pos as u8
        true
    }

    fn should_draw_corner(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        // let c = cube.corners.get_corners()[pos];
        // c.id != pos as u8
        false
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::FINLS, ""), count, false)
    }
}
