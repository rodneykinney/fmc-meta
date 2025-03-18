use pyo3::prelude::*;
use std::collections::HashMap;
use std::str::FromStr;

use pyo3::exceptions::PyValueError;
use pyo3::FromPyObject;
// use pyo3::types::PyDict;

use cubelib::algs::Algorithm as LibAlgorithm;
use cubelib::cube::turn::{ApplyAlgorithm, TransformableMut};
use cubelib::cube::{Corner, Cube333, Transformation333, Turn333};
use cubelib::defs::{NissSwitchType, StepKind as LibStepKind};
use cubelib::solver::df_search::CancelToken;
use cubelib::solver::solution::{
    ApplySolution, Solution as LibSolution, SolutionStep as LibSolutionStep,
};
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
    // fn is_ready(&self, cube: &Cube) -> PyResult<bool> {
    //     Ok(true)
    // let step_configs = vec![LibStepConfig {
    //     kind: self.0.kind,
    //     substeps: None,
    //     min: Some(0),
    //     max: Some(0),
    //     absolute_min: Some(0),
    //     absolute_max: Some(0),
    //     niss: None,
    //     step_limit: None,
    //     quality: 0,
    //     params: HashMap::new(),
    // }];
    // let mut tables = PruningTables333::new();
    // solver::gen_tables(&step_configs, &mut tables);
    // let (step, options) = &solver::build_steps(step_configs.clone(), &tables).map_err(|e| PyValueError::new_err(format!("Error building steps: {:?}", e)))?[0];
    // Ok(step.is_cube_ready(cube.0.clone()))
    //}
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
        match step {
            "eo" => match variant {
                "fb" => Ok(format!("{}e", self.0.count_bad_edges_fb())),
                "rl" => Ok(format!("{}e", self.0.count_bad_edges_lr())),
                "ud" => Ok(format!("{}e", self.0.count_bad_edges_ud())),
                _ => Ok("".to_string()),
            },
            "dr" => match variant {
                "fb" => Ok("DRFB".to_string()),
                "rl" => Ok("DRRL".to_string()),
                "ud" => {
                    let bad_corner_count = self.0.corners.get_corners().into_iter().filter(|c: &Corner| c.orientation != 0).count();
                    let bad_edge_count = self.0.count_bad_edges_lr() + self.0.count_bad_edges_fb();
                    Ok(format!("{}c{}e", bad_corner_count, bad_edge_count))
                }
                _ => Ok("".to_string()),
            },
            _ => Ok("".to_string()),
        }
    }

    fn is_step_solved(&self, step: &str, variant: &str) -> PyResult<bool> {
        match step {
            "eo" => match variant {
                "fb" => Ok(self.0.count_bad_edges_fb() == 0),
                "rl" => Ok(self.0.count_bad_edges_lr() == 0),
                "ud" => Ok(self.0.count_bad_edges_ud() == 0),
                //"" => Ok(self.0.count_bad_edges_fb() == 0 || self.0.count_bad_edges_lr() == 0 || self.0.count_bad_edges_ud() == 0),
                "" => Ok(self.is_step_solved(step, "fb").unwrap()
                    || self.is_step_solved(step, "rl").unwrap()
                    || self.is_step_solved(step, "ud").unwrap()),
                _ => Err(PyValueError::new_err(format!(
                    "Invalid EO variant '{}'",
                    variant
                ))),
            },
            "dr" => match variant {
                "fb" => {
                    let mut cube = self.0.clone();
                    cube.transform(Transformation333::X);
                    let solved = cube.count_bad_edges_fb() == 0
                        && cube.count_bad_edges_lr() == 0
                        && DRUDEOFBCoord::from(&cube).val() == 0;
                    Ok(solved)
                },
                "rl" => {
                    let mut cube = self.0.clone();
                    cube.transform(Transformation333::Z);
                    let solved = cube.count_bad_edges_fb() == 0
                        && cube.count_bad_edges_lr() == 0
                        && DRUDEOFBCoord::from(&cube).val() == 0;
                    Ok(solved)
                },
                "ud" => {
                    let solved = self.0.count_bad_edges_fb() == 0
                        && self.0.count_bad_edges_lr() == 0
                        && DRUDEOFBCoord::from(&self.0).val() == 0;
                    Ok(solved)
                },
                _ => Err(PyValueError::new_err(format!(
                    "Invalid DR variant '{}'",
                    variant
                ))),
            },
            _ => Err(PyValueError::new_err(format!("Invalid step '{}'", step))),
        }
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
                niss: niss,
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
