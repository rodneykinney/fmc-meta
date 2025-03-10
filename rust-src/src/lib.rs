use pyo3::prelude::*;
// use pyo3::exceptions::PyValueError;
// use pyo3::types::PyDict;

use cubelib::cube::Cube333;


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
        Ok(bytes.to_vec())
    }
}

// The Python module definition
#[pymodule]
fn py_cubelib(_py: Python, m: &PyModule) -> PyResult<()> {
    // Register the classes
    m.add_class::<Cube>()?;
    Ok(())
}