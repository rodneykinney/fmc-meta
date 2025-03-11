use pyo3::prelude::*;
use std::str::FromStr;
use std::collections::HashMap;

use pyo3::exceptions::PyValueError;
// use pyo3::types::PyDict;

use cubelib::algs::{Algorithm as LibAlgorithm};
use cubelib::cube::Cube333;
use cubelib::cube::turn::ApplyAlgorithm;
use cubelib::solver::solution::{Solution as LibSolution, SolutionStep as LibSolutionStep};
use cubelib::defs::{StepKind as LibStepKind, NissSwitchType};
use cubelib::solver::df_search::CancelToken;
use cubelib::steps::tables::PruningTables333;
use cubelib::steps::step::{StepConfig};
use cubelib::steps::{solver};

#[pyfunction]
fn solve(scramble: &str) -> PyResult<Vec<Solution>> {
    let alg = LibAlgorithm::from_str(scramble).map_err(|_| PyValueError::new_err("Invalid scramble"))?;
    let mut cube = Cube333::default();
    cube.apply_alg(&alg);

    let mut tables = PruningTables333::new();
    let step_configs = vec![StepConfig {
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
struct Algorithm(LibAlgorithm);

#[pyclass]
struct StepKind(LibStepKind);

#[pymethods]
impl StepKind {
    fn __repr__(&self) -> String {
        format!("{}", self.0)
    }
}

#[pymethods]
impl Algorithm {
    #[new]
    fn new(s: &str) -> PyResult<Self> {
        match LibAlgorithm::from_str(s) {
            Ok(alg) => Ok(Algorithm(alg)),
            Err(_) => Err(pyo3::exceptions::PyValueError::new_err("Invalid algorithm")),
        }
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

// The Python module definition
#[pymodule]
fn py_cubelib(_py: Python, m: &PyModule) -> PyResult<()> {
    // Register the classes
    // m.add_class::<Cube>()?;
    // m.add_class::<Algorithm>()?;
    // m.add_class::<Solution>()?;
    // m.add_class::<SolutionStep>()?;
    //m.add_class::<StepKind>()?;

    m.add_function(wrap_pyfunction!(solve, m)?)?;
    Ok(())
}