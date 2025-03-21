use pyo3::prelude::*;
use std::collections::HashMap;
use std::str::FromStr;

use pyo3::exceptions::PyValueError;
use pyo3::FromPyObject;

use cubelib::algs::Algorithm as LibAlgorithm;
use cubelib::cube::turn::{ApplyAlgorithm, CubeAxis, TransformableMut};
use cubelib::cube::{Corner, Cube333, Transformation333, Turn333};
use cubelib::defs::{NissSwitchType, StepKind as LibStepKind};
use cubelib::solver::df_search::CancelToken;
use cubelib::solver::solution::{
    ApplySolution, Solution as LibSolution, SolutionStep as LibSolutionStep,
};
use cubelib::solver_new::util_cube::CubeState;
use cubelib::steps::solver;
use cubelib::steps::step::{next_step, StepConfig as LibStepConfig};
use cubelib::steps::tables::PruningTables333;

use cubelib::steps::coord::Coord;
use cubelib::steps::dr::coords::DRUDEOFBCoord;
use cubelib::steps::eo::coords::BadEdgeCount;

#[pyclass]
struct CubeChecker {}

#[pymethods]
impl CubeChecker {
    #[new]
    fn new() -> PyResult<Self> {
        Ok(CubeChecker {})
    }
}

#[pyclass]
#[derive(FromPyObject)]
struct StepConfig {
    kind: String,
    substeps: Option<Vec<String>>,
    min: Option<u8>,
    max: Option<u8>,
    absolute_min: Option<u8>,
    absolute_max: Option<u8>,
    step_limit: Option<usize>,
    niss: Option<String>,
    params: Option<HashMap<String, String>>,
}

#[pymethods]
impl StepConfig {
    #[new]
    fn new(
        kind: String,
        niss: Option<String>,
        params: Option<HashMap<String, String>>,
        substeps: Option<Vec<String>>,
        min: Option<u8>,
        max: Option<u8>,
        absolute_min: Option<u8>,
        absolute_max: Option<u8>,
        step_limit: Option<usize>,
    ) -> PyResult<Self> {
        let _s =
            LibStepKind::from_str(&kind).map_err(|_| PyValueError::new_err("Invalid step kind"))?;
        Ok(StepConfig {
            kind: kind,
            substeps: substeps,
            min: min,
            max: max,
            absolute_min: absolute_min,
            absolute_max: absolute_max,
            niss: niss,
            step_limit: step_limit,
            params: params,
        })
    }
    #[getter]
    fn kind(&self) -> String {
        self.kind.clone()
    }
    #[getter]
    fn substeps(&self) -> Option<Vec<String>> {
        self.substeps.clone()
    }
    #[getter]
    fn min(&self) -> Option<u8> {
        self.min
    }
    #[getter]
    fn max(&self) -> Option<u8> {
        self.max
    }
    #[getter]
    fn absolute_min(&self) -> Option<u8> {
        self.absolute_min
    }
    #[getter]
    fn absolute_max(&self) -> Option<u8> {
        self.absolute_max
    }
    #[getter]
    fn step_limit(&self) -> Option<usize> {
        self.step_limit
    }
    #[getter]
    fn niss(&self) -> Option<String> {
        self.niss.clone()
    }
    #[getter]
    fn params(&self) -> Option<HashMap<String, String>> {
        self.params.clone()
    }
    fn __repr__(&self) -> String {
        format!("StepConfig {{ kind: {}, substeps: {:?}, min: {:?}, max: {:?}, absolute_min: {:?}, absolute_max: {:?}, step_limit: {:?}, niss: {:?}, params: {:?} }}", self.kind, self.substeps, self.min, self.max, self.absolute_min, self.absolute_max, self.step_limit, self.niss, self.params)
    }
}

#[pyclass]
#[derive(Clone)]
struct SolutionStep(LibSolutionStep);

#[pymethods]
impl SolutionStep {
    #[new]
    fn new(kind: String, variant: String, alg: String, comment: String) -> PyResult<Self> {
        let kind =
            LibStepKind::from_str(&kind).map_err(|_| PyValueError::new_err("Invalid step kind"))?;
        let alg =
            LibAlgorithm::from_str(&alg).map_err(|_| PyValueError::new_err("Invalid algorithm"))?;
        Ok(SolutionStep(LibSolutionStep {
            kind,
            variant,
            alg,
            comment,
        }))
    }
    #[getter]
    fn kind(&self) -> String {
        Into::<String>::into(self.0.kind.clone())
    }
    #[getter]
    fn variant(&self) -> String {
        self.0.variant.clone()
    }
    #[getter]
    fn alg(&self) -> Algorithm {
        Algorithm(self.0.alg.clone())
    }
    #[getter]
    fn comment(&self) -> String {
        self.0.comment.clone()
    }
    fn append(&mut self, move_str: &str) -> PyResult<SolutionStep> {
        let turn =
            Turn333::from_str(move_str).map_err(|_| PyValueError::new_err("Invalid move"))?;
        self.0.alg.normal_moves.push(turn);
        Ok(self.clone())
    }
}

#[pyclass]
#[derive(Clone)]
struct Solution(LibSolution);

#[pymethods]
impl Solution {
    #[new]
    fn new() -> Self {
        Solution(LibSolution::new())
    }
    #[getter]
    fn steps(&self) -> Vec<SolutionStep> {
        self.0
            .steps
            .iter()
            .map(|step| SolutionStep(step.clone()))
            .collect()
    }
    #[setter]
    fn set_steps(&mut self, steps: Vec<SolutionStep>) {
        self.0.steps = steps.iter().map(|step| step.0.clone()).collect();
    }
    #[getter]
    fn ends_on_normal(&self) -> bool {
        self.0.ends_on_normal
    }
    fn append(&mut self, step: SolutionStep) {
        self.0.steps.push(step.0.clone());
    }

    fn __repr__(&self) -> String {
        format!("{}", self.0)
    }
}

#[pyclass]
struct StepKind(LibStepKind);

#[pymethods]
impl StepKind {
    fn __repr__(&self) -> String {
        format!("{}", self.0)
    }
}

#[pyclass]
struct Algorithm(LibAlgorithm);

#[pymethods]
impl Algorithm {
    #[new]
    fn new(s: &str) -> PyResult<Self> {
        let alg =
            LibAlgorithm::from_str(s).map_err(|_| PyValueError::new_err("Invalid algorithm"))?;
        Ok(Algorithm(alg))
    }

    fn __repr__(&self) -> String {
        format!("{}", self.0)
    }
}

#[pyclass]
#[derive(Clone)]
struct Cube(Cube333);

#[pymethods]
impl Cube {
    #[new]
    fn new(scramble: String) -> PyResult<Self> {
        let alg = LibAlgorithm::from_str(&scramble)
            .map_err(|_| PyValueError::new_err("Invalid scramble"))?;
        let mut cube = Cube333::default();
        cube.apply_alg(&alg);
        Ok(Cube(cube))
    }

    fn edges(&self) -> PyResult<Vec<(u8, u8)>> {
        let bytes = self.0.edges.get_edges_raw();
        let mut edges = vec![];
        for i in 0..8 {
            let id = (bytes[0] >> (8 * i + 4) & 0xf) as u8;
            let orientation = (bytes[0] >> (8 * i + 1) & 0x7) as u8;
            edges.push((id, orientation));
        }
        for i in 0..4 {
            let id = (bytes[1] >> (8 * i + 4) & 0xf) as u8;
            let orientation = (bytes[1] >> (8 * i + 1) & 0x7) as u8;
            edges.push((id, orientation));
        }
        Ok(edges)
    }

    fn corners(&self) -> PyResult<Vec<(u8, u8)>> {
        let bytes = self.0.corners.get_corners_raw();
        let mut corners = vec![];
        for i in 0..8 {
            let id = (bytes >> (8 * i + 5) & 0x7) as u8;
            let orientation = (bytes >> (8 * i) & 0x3) as u8;
            corners.push((id, orientation));
        }
        Ok(corners)
    }

    fn apply(&mut self, solution: &Solution) {
        self.0.apply_solution(&solution.0);
    }

    fn case_name_for_step(&self, step: &str, variant: &str) -> PyResult<String> {
        Ok(StepBuilder::from_kind(step, variant)
            .map_err(|s| PyValueError::new_err(s))?
            .case_name(&self.0))
    }

    fn is_step_solved(&self, step: &str, variant: &str) -> PyResult<bool> {
        Ok(StepBuilder::from_kind(step, variant)
            .map_err(|s| PyValueError::new_err(s))?
            .is_solved(&self.0))
    }

    fn is_step_eligible(&self, step: &str, variant: &str) -> PyResult<bool> {
        Ok(StepBuilder::from_kind(step, variant)
            .map_err(|s| PyValueError::new_err(s))?
            .is_eligible(&self.0))
    }

    fn should_draw_edge(
        &self,
        step: &str,
        variant: &str,
        pos: usize,
        facelet: u8,
    ) -> PyResult<bool> {
        Ok(StepBuilder::from_kind(step, variant)
            .map_err(|s| PyValueError::new_err(s))?
            .should_draw_edge(&self.0, pos, facelet))
    }
    fn should_draw_corner(
        &self,
        step: &str,
        variant: &str,
        pos: usize,
        facelet: u8,
    ) -> PyResult<bool> {
        Ok(StepBuilder::from_kind(step, variant)
            .map_err(|s| PyValueError::new_err(s))?
            .should_draw_corner(&self.0, pos, facelet))
    }
    fn debug(&self, _pos: usize, _facelet: u8) -> String {
        "Hello".to_string()
    }
}

#[pyfunction]
fn solve_step(
    cube: Cube,
    step_config: StepConfig,
    solutions: Vec<Solution>,
) -> PyResult<Vec<Solution>> {
    // let alg = LibAlgorithm::from_str(&scramble).map_err(|_| PyValueError::new_err("Invalid scramble"))?;
    // let mut cube = Cube333::default();
    // cube.apply_alg(&alg);

    let step_configs = vec![step_config]
        .into_iter()
        .map(|s| {
            let niss = s.niss.as_ref().map(|n| match n.as_str() {
                "never" => NissSwitchType::Never,
                "always" => NissSwitchType::Always,
                "before" => NissSwitchType::Before,
                _ => NissSwitchType::Never,
            });
            LibStepConfig {
                kind: LibStepKind::from_str(&s.kind).unwrap(),
                substeps: s.substeps,
                min: s.min,
                max: s.max,
                absolute_min: s.absolute_min,
                absolute_max: s.absolute_max,
                niss,
                step_limit: s.step_limit,
                quality: 0,
                params: s.params.unwrap_or_default(),
            }
        })
        .collect();

    let mut tables = PruningTables333::new();
    solver::gen_tables(&step_configs, &mut tables);
    let (step, options) = &solver::build_steps(step_configs.clone(), &tables)
        .map_err(|e| PyValueError::new_err(format!("Error building steps: {:?}", e)))?[0];

    let cancel_token = CancelToken::default();
    let solutions = if solutions.is_empty() {
        vec![Solution(LibSolution::new())]
    } else {
        solutions
    };
    // let solutions = cubelib::solver::solve_steps(cube.0, &steps, &CancelToken::default());
    // Ok(solutions.into_iter().map(Solution).collect())
    let solutions: Vec<Solution> = solutions
        .iter()
        .flat_map(|solution| {
            next_step(
                vec![solution.0.clone()].into_iter(),
                &step,
                options.clone(),
                cube.0.clone(),
                &cancel_token,
            )
                .map(|s| Solution(s))
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>();
    Ok(solutions)
}

// The Python module definition
#[pymodule]
fn py_cubelib(_py: Python, m: &PyModule) -> PyResult<()> {
    // Register the classes
    m.add_class::<Cube>()?;
    m.add_class::<Algorithm>()?;
    m.add_class::<Solution>()?;
    m.add_class::<SolutionStep>()?;
    m.add_class::<StepConfig>()?;
    m.add("foo", PyModule::new(_py, "StepKind")?)?;

    m.add_function(wrap_pyfunction!(solve_step, m)?)?;
    Ok(())
}

trait Solvable {
    fn is_solved(&self, cube: &Cube333) -> bool;
    fn is_eligible(&self, cube: &Cube333) -> bool;
    fn case_name(&self, cube: &Cube333) -> String;
    fn should_draw_edge(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool;
    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool;
}
struct StepBuilder;
impl StepBuilder {
    fn from_kind(kind: &str, variant: &str) -> Result<Box<dyn Solvable>, String> {
        match kind {
            "eo" => match variant {
                "fb" => Ok(Box::new(EOFB)),
                "rl" => Ok(Box::new(EORL)),
                "ud" => Ok(Box::new(EOUD)),
                _ => Err(format!("Unknown variant '{}' for eo", variant).into()),
            },
            "dr" => match variant {
                "fb" => Ok(Box::new(DRFB)),
                "rl" => Ok(Box::new(DRRL)),
                "ud" => Ok(Box::new(DRUD)),
                _ => Err(format!("Unknown variant '{}' for dr", variant).into()),
            },
            "htr" => match variant {
                "fb" => Ok(Box::new(HTRFB)),
                "rl" => Ok(Box::new(HTRRL)),
                "ud" => Ok(Box::new(HTRUD)),
                _ => Err(format!("Unknown variant '{}' for dr", variant).into()),
            },
            "" => Ok(Box::new(SCRAMBLED)),
            _ => Err(format!("Unknown kind '{}'", kind).into()),
        }
    }
}

pub struct SCRAMBLED;
impl Solvable for SCRAMBLED {
    fn is_solved(&self, _cube: &Cube333) -> bool {
        true
    }
    fn is_eligible(&self, _cube: &Cube333) -> bool {
        true
    }
    fn case_name(&self, _cube: &Cube333) -> String {
        "".to_string()
    }
    fn should_draw_edge(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        true
    }
    fn should_draw_corner(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        true
    }
}

pub struct EOFB;
pub struct EORL;
pub struct EOUD;
impl Solvable for EOFB {
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
}
impl Solvable for EORL {
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
}
impl Solvable for EOUD {
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
}
pub struct DRUD;
pub struct DRRL;
pub struct DRFB;

impl Solvable for DRUD {
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
        c.orientation != 0 && c.orientation == facelet
    }
}
impl Solvable for DRFB {
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
        let is_bad = match (c.id + pos as u8) % 2 {
            0 => c.orientation != 0,
            _ => c.orientation != 2 - (c.id % 2),
        };
        is_bad && facelet == (c.orientation + 2 - (c.id % 2)) % 3
    }
}
impl Solvable for DRRL {
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
        let is_bad = match (c.id + pos as u8) % 2 {
            0 => c.orientation != 0,
            _ => c.orientation != 1 + (c.id % 2),
        };
        is_bad && facelet == (c.orientation + 1 + (c.id % 2)) % 3
    }
}

pub struct HTRUD;
pub struct HTRFB;
pub struct HTRRL;
impl Solvable for HTRUD {
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
        !cube.edges.get_edges()[pos].oriented_ud && facelet == 1
    }
    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        let pos = pos as u8;
        match (c.id + pos) % 2 {
            1 => {
                // Bad corner
                match c.id / 4 {
                    1 => facelet == 0, // Draw D
                    _ => c.orientation != facelet,
                }
            }
            0 => {
                // In home orbit
                match c.id / 4 {
                    1 => facelet == 0,
                    _ => false
                }
            }
            _ => false,
        }
    }
}
impl Solvable for HTRFB {
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
        if !e.oriented_fb {
            match e.id {
                4 | 5 | 6 | 7 => facelet == 1,
                _ => facelet == 0,
            }
        } else {
            false
        }
    }
    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        let pos = pos as u8;
        match (c.id + pos) % 2 {
            1 => {
                // Bad corner
                match c.id  {
                    0 | 3 | 4 | 7 => facelet == 1 + (c.id % 2), // Draw L
                    _ => c.orientation != 2 - (c.id % 2)
                }
            }
            0 => {
                // In home orbit
                match c.id  {
                    0 | 3 | 4 | 7 => facelet == 1 + (c.id % 2), // Draw L
                    _ => false
                }
            }
            _ => false,
        }
    }
}
impl Solvable for HTRRL {
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
        !cube.edges.get_edges()[pos].oriented_rl && facelet == 0
    }
    fn should_draw_corner(&self, cube: &Cube333, pos: usize, facelet: u8) -> bool {
        let c = cube.corners.get_corners()[pos];
        let pos = pos as u8;
        match (c.id + pos) % 2 {
            1 => {
                // Bad corner
                match c.id  {
                    0 | 3 | 4 | 7 => true, // Draw L
                    _ => facelet != 2 - (c.id % 2) // facelet == 2 - (c.id % 2) // false, //facelet == 2 - (c.id % 2) // c.orientation != (facelet + 1 + (c.id % 2)) % 3
                }
            }
            0 => {
                // Bad odd
                // draw if face=1, o=1
                // bad even
                // draw if face=2, o=2
                // Good corner c.id % 2 == 0
                // draw if face=1
                // Good corner, c.id % 2 == 1
                // draw if face=2
                // In home orbit
                match c.id  {
                    0 | 3 | 4 | 7 => facelet == 1 + (c.id % 2), // Draw L
                    _ => false // facelet == 1 + (c.id % 2), // facelet == 2 - (c.id % 2) // false
                }
            }
            _ => false,
        }
    }
}
