use cubelib::algs::Algorithm as LibAlgorithm;
use cubelib::cube::turn::CubeOuterTurn;
use cubelib::cube::Cube333;
use cubelib::cube::Direction;
use cubelib::defs::StepKind;
use cubelib::solver::df_search::CancelToken;
use cubelib::steps::solver::{build_steps, gen_tables};
use cubelib::steps::step::StepConfig;
use cubelib::steps::tables::PruningTables333;
use pyo3::exceptions::PyValueError;
use pyo3::{pyfunction, PyResult};

use crate::Algorithm;

#[pyfunction]
pub fn scramble() -> PyResult<String> {
    let cube = Cube333::random(&mut rand::rng());

    let mut tables = PruningTables333::new();

    let step_configs = vec![
        step_config(StepKind::EO, "", Some(6)),
        step_config(StepKind::DR, "", None),
        step_config(StepKind::HTR, "", None),
        step_config(StepKind::FIN, "", None),
    ];
    gen_tables(&step_configs, &mut tables);

    let steps = build_steps(step_configs, &tables).map_err(|e| PyValueError::new_err(e))?;
    let cancel_token = CancelToken::default();
    let mut solutions = cubelib::solver::solve_steps(cube, &steps, &cancel_token);

    let solution = solutions
        .next()
        .ok_or_else(|| PyValueError::new_err("No solutions found"))?;
    let alg = Into::<LibAlgorithm>::into(solution);
    let mut moves = alg.normal_moves.clone();
    let mut imoves = alg.inverse_moves.clone();
    imoves.reverse();
    moves.append(&mut imoves);
    let alg = LibAlgorithm {
        normal_moves: moves,
        inverse_moves: vec![],
    };
    Ok(format!("{}", alg))
}

pub fn step_config(kind: StepKind, variant: &str, max: Option<u8>) -> StepConfig {
    let substeps = match variant {
        "" => None,
        s => Some(vec![s.to_string()]),
    };
    StepConfig {
        kind: kind,
        substeps: substeps,
        min: None,
        max: max,
        absolute_min: None,
        absolute_max: None,
        step_limit: None,
        quality: 100,
        niss: None,
        params: Default::default(),
    }
}

pub fn solve_step(cube: &Cube333, cfg: StepConfig) -> PyResult<Vec<Algorithm>> {
    let mut tables = PruningTables333::new();

    let step_configs = match cfg.kind {
        StepKind::DR => vec![
            step_config(StepKind::EO, "", Some(0)),
            cfg.clone()
        ],
        StepKind::HTR => vec![
            step_config(StepKind::EO, "", Some(0)),
            step_config(StepKind::DR, "", Some(0)),
            cfg.clone(),
        ],
        StepKind::FR | StepKind::FINLS => vec![
            step_config(StepKind::EO, "", Some(0)),
            step_config(StepKind::DR, "", Some(0)),
            step_config(StepKind::HTR, "", Some(0)),
            cfg.clone(),
        ],
        _ => vec![cfg.clone()],
    };
    gen_tables(&step_configs, &mut tables);

    let steps = build_steps(step_configs, &tables).map_err(|e| PyValueError::new_err(e))?;
    let cancel_token = CancelToken::default();
    let solutions = cubelib::solver::solve_steps(cube.clone(), &steps, &cancel_token);
    let algs = match cfg.kind {
        StepKind::FIN | StepKind::FR => solutions
            .map(Into::<LibAlgorithm>::into)
            .map(Algorithm)
            .take(100)
            .collect(),
        _ => solutions
            .map(Into::<LibAlgorithm>::into)
            .map(Algorithm)
            .filter(is_canonical)
            .take(100)
            .collect(),
    };
    Ok(algs)
}

fn is_canonical(alg: &Algorithm) -> bool {
    fn is_canonical(vec: &Vec<CubeOuterTurn>) -> bool {
        match vec.len() {
            0 => true,
            1 => vec[0].dir != Direction::CounterClockwise,
            n => {
                vec[n - 1].dir != Direction::CounterClockwise
                    && (vec[n - 2].face != vec[n - 1].face.opposite()
                        || vec[n - 2].dir != Direction::CounterClockwise)
            }
        }
    }
    is_canonical(&alg.0.normal_moves) && is_canonical(&alg.0.inverse_moves)
}
