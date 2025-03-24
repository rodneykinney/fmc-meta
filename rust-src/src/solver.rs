use cubelib::steps::tables::PruningTables333;


pub struct Solver {
    tables: PruningTables333,
}

impl Solver {
    pub fn new() -> Self {
        let mut tables = PruningTables333::new();
        tables.gen_eo();
        tables.gen_dr();
        tables.gen_htr();
        tables.gen_fr();
        Solver { tables }
    }
}
