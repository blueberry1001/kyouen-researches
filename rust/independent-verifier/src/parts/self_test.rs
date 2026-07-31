pub fn run_reference_self_test() -> Result<Vec<String>, String> {
    let mut messages = Vec::new();

    // Geometry checks use shapes whose status is easy to inspect manually.
    if !is_forbidden_quad(4, 0, 1, 4, 5) {
        return Err("the four corners of a unit square must be concyclic".into());
    }
    if !is_forbidden_quad(4, 0, 1, 2, 3) {
        return Err("four collinear points must be forbidden".into());
    }
    if is_forbidden_quad(4, 0, 1, 4, 10) {
        return Err("chosen non-concyclic quadruple was incorrectly rejected".into());
    }
    messages.push("geometry examples: OK".into());

    let board4 = BoardSpec::new(4).map_err(|e| e.to_string())?;
    let three_square_corners = board4
        .mask_from_ids([0, 1, 4])
        .map_err(|e| e.to_string())?;
    let legal = board4
        .legal_mask(three_square_corners)
        .map_err(|e| e.to_string())?;
    if legal & bit(5) != 0 {
        return Err("the fourth corner of a unit square should be illegal".into());
    }
    messages.push("from-scratch legal-move reconstruction: OK".into());

    // Expected values were independently enumerated with a tiny brute-force
    // script before being embedded here.
    let expected = [
        (1usize, Outcome::Winning, 1usize),
        (2usize, Outcome::Winning, 4usize),
        (3usize, Outcome::Winning, 9usize),
        (4usize, Outcome::Losing, 0usize),
    ];
    for (size, expected_empty, expected_winning_first_moves) in expected {
        let board = BoardSpec::new(size).map_err(|e| e.to_string())?;
        let mut solver = Solver::new(&board, SolveOptions::default());
        let actual_empty = solver.solve(0).map_err(|e| e.to_string())?;
        if actual_empty != expected_empty {
            return Err(format!(
                "{size}x{size}: empty-board result {actual_empty}, expected {expected_empty}"
            ));
        }
        let rows = classify_first_moves(&board, SolveOptions::default())
            .map_err(|e| e.to_string())?;
        let winning_count = rows
            .iter()
            .filter(|r| r.result_for_first_player == Outcome::Winning)
            .count();
        if winning_count != expected_winning_first_moves {
            return Err(format!(
                "{size}x{size}: {winning_count} winning first moves, expected {expected_winning_first_moves}"
            ));
        }
        messages.push(format!(
            "{size}x{size}: empty={actual_empty}, winning first moves={winning_count}: OK"
        ));
    }

    Ok(messages)
}

pub fn evidence_candidate_dirs(root: &Path) -> Vec<PathBuf> {
    let mut result = Vec::new();
    if root.join("10x10-first-move-classification-complete.csv").exists() {
        result.push(root.to_path_buf());
    }
    if let Ok(entries) = fs::read_dir(root) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir()
                && path
                    .join("10x10-first-move-classification-complete.csv")
                    .exists()
            {
                result.push(path);
            }
        }
    }
    result
}
