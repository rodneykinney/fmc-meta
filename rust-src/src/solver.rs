use cubelib::algs::Algorithm as LibAlgorithm;
use cubelib::cube::turn::CubeOuterTurn;
use cubelib::cube::Cube333;
use cubelib::cube::Direction;
use cubelib::defs::StepKind;
use cubelib::solver::df_search::CancelToken;
use cubelib::solver::solve_steps;
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
    let mut solutions = solve_steps(cube, &steps, &cancel_token);

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
        quality: 0,
        niss: None,
        params: Default::default(),
    }
}

fn dummy(_: &Algorithm) -> bool {
    true
}

pub fn solve_step(
    cube: &Cube333,
    cfg: StepConfig,
    n: usize,
    require_canonical: bool,
) -> Result<Vec<Algorithm>, String> {
    solve_step_impl(cube, cfg, n, require_canonical, false, dummy)
}

pub fn solve_step_deduplicated<F, T>(
    cube: &Cube333,
    cfg: StepConfig,
    n: usize,
    require_canonical: bool,
    unique_fn: F,
) -> Result<Vec<Algorithm>, String>
where
    F: Fn(&Algorithm) -> T,
    T: Eq + std::hash::Hash,
{
    solve_step_impl(cube, cfg, n, require_canonical, true, unique_fn)
}

fn solve_step_impl<F, T>(
    cube: &Cube333,
    cfg: StepConfig,
    n: usize,
    require_canonical: bool,
    require_unique: bool,
    unique_fn: F,
) -> Result<Vec<Algorithm>, String>
where
    F: Fn(&Algorithm) -> T,
    T: Eq + std::hash::Hash,
{
    let mut tables = Box::new(PruningTables333::new());
    let step_configs = match cfg.kind {
        StepKind::DR => vec![step_config(StepKind::EO, "", Some(0)), cfg.clone()],
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

    let steps = build_steps(step_configs, &tables)?;
    let cancel_token = CancelToken::default();
    let algs = solve_steps(cube.clone(), &steps, &cancel_token)
        .map(Into::<LibAlgorithm>::into)
        .map(Algorithm);
    let algs = algs.filter(|a| !require_canonical || is_canonical(a));
    match require_unique {
        true => {
            let mut unique = std::collections::HashSet::new();
            let mut v = Vec::new();
            for alg in algs {
                let key = unique_fn(&alg);
                if unique.insert(key) {
                    v.push(alg);
                }
                if v.len() >= n {
                    break;
                }
            }
            Ok(v)
        }
        false => Ok(algs.take(n).collect()),
    }
}

pub fn is_canonical(alg: &Algorithm) -> bool {
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
