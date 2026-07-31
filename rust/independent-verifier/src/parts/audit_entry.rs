#[derive(Debug, Clone, Default)]
pub struct AuditReport {
    pub checked_files: usize,
    pub checked_rows: usize,
    pub issues: Vec<String>,
}

impl AuditReport {
    pub fn is_ok(&self) -> bool {
        self.issues.is_empty()
    }
}

pub fn audit_evidence_dir(dir: &Path) -> Result<AuditReport, BoardError> {
    let board = BoardSpec::new(10)?;
    let mut report = AuditReport::default();

    let classification_path = dir.join("10x10-first-move-classification-complete.csv");
    let all_moves_path = dir.join("10x10-all-first-moves-winning-replies.csv");

    let classification = read_csv_table(&classification_path)
        .map_err(|e| BoardError(format!("{}: {e}", classification_path.display())))?;
    report.checked_files += 1;
    audit_classification(&board, &classification, &mut report);

    let all_moves = read_csv_table(&all_moves_path)
        .map_err(|e| BoardError(format!("{}: {e}", all_moves_path.display())))?;
    report.checked_files += 1;
    audit_all_moves(&board, &classification, &all_moves, &mut report);

    let entries = fs::read_dir(dir)
        .map_err(|e| BoardError(format!("cannot read {}: {e}", dir.display())))?;
    for entry in entries {
        let entry = entry.map_err(|e| BoardError(format!("cannot read directory entry: {e}")))?;
        let path = entry.path();
        let Some(name) = path.file_name().and_then(|s| s.to_str()) else {
            continue;
        };
        if !name.starts_with("10x10-children-") || !name.ends_with(".csv") {
            continue;
        }
        let table = read_csv_table(&path)
            .map_err(|e| BoardError(format!("{}: {e}", path.display())))?;
        report.checked_files += 1;
        audit_child_proof(&board, name, &table, &mut report);
    }

    Ok(report)
}
