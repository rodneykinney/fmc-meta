use crate::{Solvable, CORNER_FB_FACELETS, CORNER_OPPOSITE_E_SLICE, CORNER_OPPOSITE_M_SLICE, CORNER_OPPOSITE_S_SLICE, CORNER_RL_FACELETS, CORNER_UD_FACELETS, EDGE_FB_FACELETS, EDGE_OPPOSITE_E_SLICE, EDGE_OPPOSITE_M_SLICE, EDGE_OPPOSITE_S_SLICE, EDGE_RL_FACELETS, EDGE_UD_FACELETS, HTRFB, HTRRL, HTRUD};
use cubelib::cube::turn::TransformableMut;
use cubelib::cube::{Cube333, CubeFace, Direction, Transformation333, Turn333};
use cubelib::steps::coord::Coord;
use cubelib::steps::fr::coords::{FRCPOrbitCoord, FROrbitParityCoord, FRUDNoSliceCoord};
use pyo3::exceptions::PyValueError;
use pyo3::PyResult;
use std::str::FromStr;

pub struct FRUD;
impl Solvable for FRUD {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        let turn = Turn333::from_str(s).map_err(|_| PyValueError::new_err("Invalid move"))?;
        match turn.face {
            CubeFace::Up | CubeFace::Down => Ok(false),
            _ => Ok(turn.dir == Direction::Half),
        }
    }

    fn is_solved(&self, cube: &Cube333) -> bool {
        FRUDNoSliceCoord::from(cube).val() == 0
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRUD.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let parity = FROrbitParityCoord::from(cube).val() == 1;
        let corner_case = match (FRCPOrbitCoord::from(&cube.corners).val(), parity) {
            (0, true) => "0c3",
            (0, false) => "0c0",
            (3, true) => "4c1",
            (3, false) => "4c2",
            (_, true) => "6c1",
            (_, false) => "6c2",
        };
        let bad_edge_count = cube
            .edges
            .get_edges()
            .iter()
            .enumerate()
            .filter(|(pos, e)|
                *pos as u8 != EDGE_OPPOSITE_E_SLICE[*pos]
                    && e.id != *pos as u8
                    && e.id != EDGE_OPPOSITE_E_SLICE[*pos])
            .count() as u8;
        let bad_edge_count = bad_edge_count.min(8 - bad_edge_count);

        format!("{} {}e", corner_case, bad_edge_count).to_string()
    }

    fn should_draw_edge(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let e = cube.edges.get_edges()[pos];
        pos as u8 != EDGE_OPPOSITE_E_SLICE[pos]
            && e.id != pos as u8
            && e.id != EDGE_OPPOSITE_E_SLICE[pos]
            && Some(facelet) != EDGE_UD_FACELETS[pos]
    }

    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        let c_opp = cube.corners.get_corners()[CORNER_OPPOSITE_E_SLICE[pos] as usize];
        match c.id {
            2 | 5 => {
                c_opp.id != CORNER_OPPOSITE_E_SLICE[c.id as usize]
                    && facelet != CORNER_UD_FACELETS[pos]
            }
            _ => false,
        }
    }
}
pub struct FRFB;
impl Solvable for crate::FRFB {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        let turn = Turn333::from_str(s).map_err(|_| PyValueError::new_err("Invalid move"))?;
        match turn.face {
            CubeFace::Front | CubeFace::Back => Ok(false),
            _ => Ok(turn.dir == Direction::Half),
        }
    }

    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::X);
        FRUD.is_solved(&cube)
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRFB.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let mut ud_cube = cube.clone();
        ud_cube.transform(Transformation333::X);
        let parity = FROrbitParityCoord::from(&ud_cube).val() == 1;
        let corner_case = match (FRCPOrbitCoord::from(&ud_cube.corners).val(), parity) {
            (0, true) => "0c3",
            (0, false) => "0c0",
            (3, true) => "4c1",
            (3, false) => "4c2",
            (_, true) => "6c1",
            (_, false) => "6c2",
        };
        let bad_edge_count = cube
            .edges
            .get_edges()
            .iter()
            .enumerate()
            .filter(|(pos, e)|
                *pos as u8 != EDGE_OPPOSITE_S_SLICE[*pos]
                    && e.id != *pos as u8
                    && e.id != EDGE_OPPOSITE_S_SLICE[*pos])
            .count() as u8;
        let bad_edge_count = bad_edge_count.min(8 - bad_edge_count);

        format!("{} {}e", corner_case, bad_edge_count).to_string()
    }

    fn should_draw_edge(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let e = cube.edges.get_edges()[pos];
        pos as u8 != EDGE_OPPOSITE_S_SLICE[pos]
            && e.id != pos as u8
            && e.id != EDGE_OPPOSITE_S_SLICE[pos]
            && Some(facelet) != EDGE_FB_FACELETS[pos]
    }

    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        let c_opp = cube.corners.get_corners()[CORNER_OPPOSITE_S_SLICE[pos] as usize];
        match c.id {
            1 | 2 => {
                c_opp.id != CORNER_OPPOSITE_S_SLICE[c.id as usize]
                    && facelet != CORNER_FB_FACELETS[pos]
            }
            _ => false,
        }
    }
}

pub struct FRRL;
impl Solvable for FRRL {
    fn is_move_allowed(&self, s: &str) -> PyResult<bool> {
        let turn = Turn333::from_str(s).map_err(|_| PyValueError::new_err("Invalid move"))?;
        match turn.face {
            CubeFace::Right | CubeFace::Left => Ok(false),
            _ => Ok(turn.dir == Direction::Half),
        }
    }

    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Z);
        FRUD.is_solved(&cube)
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRRL.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let mut ud_cube = cube.clone();
        ud_cube.transform(Transformation333::X);
        let parity = FROrbitParityCoord::from(&ud_cube).val() == 1;
        let corner_case = match (FRCPOrbitCoord::from(&ud_cube.corners).val(), parity) {
            (0, true) => "0c3",
            (0, false) => "0c0",
            (3, true) => "4c1",
            (3, false) => "4c2",
            (_, true) => "6c1",
            (_, false) => "6c2",
        };
        let bad_edge_count = cube
            .edges
            .get_edges()
            .iter()
            .enumerate()
            .filter(|(pos, e)|
                *pos as u8 != EDGE_OPPOSITE_M_SLICE[*pos]
                    && e.id != *pos as u8
                    && e.id != EDGE_OPPOSITE_M_SLICE[*pos])
            .count() as u8;
        let bad_edge_count = bad_edge_count.min(8 - bad_edge_count);

        format!("{} {}e", corner_case, bad_edge_count).to_string()
    }

    fn should_draw_edge(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let e = cube.edges.get_edges()[pos];
        pos as u8 != EDGE_OPPOSITE_M_SLICE[pos]
            && e.id != pos as u8
            && e.id != EDGE_OPPOSITE_M_SLICE[pos]
            && Some(facelet) != EDGE_RL_FACELETS[pos]
    }

    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        let c_opp = cube.corners.get_corners()[CORNER_OPPOSITE_M_SLICE[pos] as usize];
        match c.id {
            2 | 3 => {
                c_opp.id != CORNER_OPPOSITE_M_SLICE[c.id as usize]
                    && facelet != CORNER_RL_FACELETS[pos]
            }
            _ => false,
        }
    }
}

