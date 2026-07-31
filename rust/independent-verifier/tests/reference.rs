use kyouen_verifier::{BoardSpec, Outcome, SolveOptions, Solver};

#[test]
fn four_by_four_empty_position_is_losing() {
    let board = BoardSpec::new(4).unwrap();
    let mut solver = Solver::new(&board, SolveOptions::default());
    assert_eq!(solver.solve(0).unwrap(), Outcome::Losing);
}

#[test]
fn one_by_one_empty_position_is_winning() {
    let board = BoardSpec::new(1).unwrap();
    let mut solver = Solver::new(&board, SolveOptions::default());
    assert_eq!(solver.solve(0).unwrap(), Outcome::Winning);
    assert_eq!(solver.winning_move(0).unwrap(), Some(0));
}
