use pyo3::prelude::*;
use std::str::FromStr;
use std::collections::HashMap;

use pyo3::exceptions::PyValueError;
use pyo3::FromPyObject;
// use pyo3::types::PyDict;

use cubelib::algs::{Algorithm as LibAlgorithm};
use cubelib::cube::Cube333;
use cubelib::cube::turn::ApplyAlgorithm;
use cubelib::solver::solution::{Solution as LibSolution, SolutionStep as LibSolutionStep};
use cubelib::defs::{StepKind as LibStepKind, NissSwitchType};
use cubelib::solver::df_search::CancelToken;
use cubelib::steps::tables::PruningTables333;
use cubelib::steps::step::{StepConfig as LibStepConfig, next_step};
use cubelib::steps::{solver};

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
    fn new(kind: String, niss: Option<String>, params: Option<HashMap<String, String>>, substeps: Option<Vec<String>>, min: Option<u8>, max: Option<u8>, absolute_min: Option<u8>, absolute_max: Option<u8>, step_limit: Option<usize>) -> PyResult<Self> {
        let _s = LibStepKind::from_str(&kind).map_err(|_| PyValueError::new_err("Invalid step kind"))?;
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
struct SolutionStep(LibSolutionStep);

#[pymethods]
impl SolutionStep {
    #[new]
    fn new(kind: String, variant: String, alg: String, comment: String) -> PyResult<Self> {
        let kind = LibStepKind::from_str(&kind).map_err(|_| PyValueError::new_err("Invalid step kind"))?;
        let alg = LibAlgorithm::from_str(&alg).map_err(|_| PyValueError::new_err("Invalid algorithm"))?;
        Ok(SolutionStep(LibSolutionStep {
            kind,
            variant,
            alg,
            comment,
        }))
    }
    #[getter]
    fn kind(&self) -> StepKind {
        StepKind(self.0.kind.clone())
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
}

#[pyclass]
#[derive(Clone)]
struct Solution(LibSolution);

#[pymethods]
impl Solution {
    #[getter]
    fn steps(&self) -> Vec<SolutionStep> {
        self.0.steps.iter().map(|step| SolutionStep(step.clone())).collect()
    }
    #[getter]
    fn ends_on_normal(&self) -> bool {
        self.0.ends_on_normal
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
        let alg = LibAlgorithm::from_str(s).map_err(|_| PyValueError::new_err("Invalid algorithm"))?;
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
        let alg = LibAlgorithm::from_str(&scramble).map_err(|_| PyValueError::new_err("Invalid scramble"))?;
        let mut cube = Cube333::default();
        cube.apply_alg(&alg);
        Ok(Cube(cube))
    }

    fn edges(&self) -> PyResult<Vec<u64>> {
        let bytes = self.0.edges.get_edges_raw();
        let mut edges = vec![];
        for i in 0..8 {
            edges.push(bytes[0] << (8 * i) & 0xff);
        }
        for i in 0..4 {
            edges.push(bytes[1] << (8 * i) & 0xff);
        }
        Ok(edges)
    }
}

#[pyfunction]
fn solve_step(cube: Cube, solutions: Vec<Solution>, step_config: StepConfig) -> PyResult<Vec<Solution>> {
    // let alg = LibAlgorithm::from_str(&scramble).map_err(|_| PyValueError::new_err("Invalid scramble"))?;
    // let mut cube = Cube333::default();
    // cube.apply_alg(&alg);

    let mut tables = PruningTables333::new();
    let step_configs = vec![step_config].into_iter().map(|s| {
        let niss = s.niss.as_ref().map(|n| {
            match n.as_str() {
                "never" => NissSwitchType::Never,
                "always" => NissSwitchType::Always,
                "before" => NissSwitchType::Before,
                _ => NissSwitchType::Never,
            }
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
    }).collect();

    solver::gen_tables(&step_configs, &mut tables);
    let s = &solver::build_steps(step_configs.clone(), &tables).map_err(|e| PyValueError::new_err(format!("Error building steps: {:?}", e)))?[0];

    let cancel_token = CancelToken::default();
    // let solutions = cubelib::solver::solve_steps(cube.0, &steps, &CancelToken::default());
    // Ok(solutions.into_iter().map(Solution).collect())
    let solutions: Vec<Solution> = solutions
        .iter()
        .flat_map(|solution| {
            next_step(
                vec![solution.0.clone()].into_iter(),
                &s.0,
                s.1.clone(),
                cube.0.clone(),
                &cancel_token,
            ).map(|s| Solution(s)).collect::<Vec<_>>()
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

    m.add_function(wrap_pyfunction!(solve_step, m)?)?;
    Ok(())
}