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
use cubelib::steps::step::{StepConfig as LibStepConfig};
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
}

#[pyclass]
struct SolutionStep(LibSolutionStep);

#[pymethods]
impl SolutionStep {
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
struct Cube {
    cube: Cube333,
}

#[pymethods]
impl Cube {
    #[new]
    fn new() -> Self {
        Cube {
            cube: Cube333::random(&mut rand::rng()),
        }
    }

    fn edges(&self) -> PyResult<Vec<u64>> {
        let bytes = self.cube.edges.get_edges_raw();
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
fn solve(scramble: &str, step_configs: Vec<StepConfig>) -> PyResult<Vec<Solution>> {
    let alg = LibAlgorithm::from_str(scramble).map_err(|_| PyValueError::new_err("Invalid scramble"))?;
    let mut cube = Cube333::default();
    cube.apply_alg(&alg);

    let mut tables = PruningTables333::new();
    let step_configs = vec![LibStepConfig {
        kind: LibStepKind::EO,
        substeps: None,
        min: None,
        max: None,
        absolute_min: None,
        absolute_max: None,
        niss: Some(NissSwitchType::Never),
        step_limit: None,
        quality: 0,
        params: HashMap::new(),
    }];

    solver::gen_tables(&step_configs, &mut tables);
    let steps = solver::build_steps(step_configs, &tables).map_err(|e| PyValueError::new_err(format!("Error building steps: {:?}", e)))?;

    let solutions = cubelib::solver::solve_steps(cube, &steps, &CancelToken::default());
    Ok(solutions.into_iter().map(Solution).collect())
}



// The Python module definition
#[pymodule]
fn py_cubelib(_py: Python, m: &PyModule) -> PyResult<()> {
    // Register the classes
    // m.add_class::<Cube>()?;
    // m.add_class::<Algorithm>()?;
    // m.add_class::<Solution>()?;
    // m.add_class::<SolutionStep>()?;
    m.add_class::<StepConfig>()?;

    m.add_function(wrap_pyfunction!(solve, m)?)?;
    Ok(())
}