fn audit_classification(board: &BoardSpec, table: &CsvTable, report: &mut AuditReport) {
    if table.rows.len() != 15 {
        report.issues.push(format!(
            "classification has {} rows; expected 15 representatives",
            table.rows.len()
        ));
    }
    let mut first_ids = HashSet::new();
    for (row_index, row) in table.rows.iter().enumerate() {
        report.checked_rows += 1;
        let context = format!("classification row {}", row_index + 2);
        let Some(first) = parse_usize_cell(table, row, "first_id", &context, report) else {
            continue;
        };
        let Some(first_x) = parse_usize_cell(table, row, "first_x", &context, report) else {
            continue;
        };
        let Some(first_y) = parse_usize_cell(table, row, "first_y", &context, report) else {
            continue;
        };
        let Some(reply) = parse_usize_cell(table, row, "winning_second_reply_id", &context, report) else {
            continue;
        };
        let Some(reply_x) = parse_usize_cell(table, row, "reply_x", &context, report) else {
            continue;
        };
        let Some(reply_y) = parse_usize_cell(table, row, "reply_y", &context, report) else {
            continue;
        };
        if !first_ids.insert(first) {
            report.issues.push(format!("{context}: duplicate first_id {first}"));
        }
        if first != first_y * board.size() + first_x {
            report.issues.push(format!("{context}: first id and coordinates disagree"));
        }
        if reply != reply_y * board.size() + reply_x {
            report.issues.push(format!("{context}: reply id and coordinates disagree"));
        }
        if first == reply {
            report.issues.push(format!("{context}: reply repeats the first move"));
        }
        if cell(table, row, "result_for_first_player") != Some("LOSS") {
            report.issues.push(format!("{context}: expected first-player result LOSS"));
        }
    }
}

fn audit_all_moves(
    board: &BoardSpec,
    classification: &CsvTable,
    table: &CsvTable,
    report: &mut AuditReport,
) {
    if table.rows.len() != board.point_count() {
        report.issues.push(format!(
            "all-first-moves table has {} rows; expected {}",
            table.rows.len(),
            board.point_count()
        ));
    }

    let mut representative_reply = HashMap::new();
    for row in &classification.rows {
        let first = cell(classification, row, "first_id").and_then(|s| s.parse::<usize>().ok());
        let reply = cell(classification, row, "winning_second_reply_id")
            .and_then(|s| s.parse::<usize>().ok());
        if let (Some(first), Some(reply)) = (first, reply) {
            representative_reply.insert(first, reply);
        }
    }

    let mut ids = HashSet::new();
    for (row_index, row) in table.rows.iter().enumerate() {
        report.checked_rows += 1;
        let context = format!("all-first-moves row {}", row_index + 2);
        let Some(first) = parse_usize_cell(table, row, "first_id", &context, report) else {
            continue;
        };
        let Some(first_x) = parse_usize_cell(table, row, "first_x", &context, report) else {
            continue;
        };
        let Some(first_y) = parse_usize_cell(table, row, "first_y", &context, report) else {
            continue;
        };
        let Some(representative) = parse_usize_cell(table, row, "representative_id", &context, report) else {
            continue;
        };
        let Some(transform) = parse_usize_cell(table, row, "transform_to_representative", &context, report) else {
            continue;
        };
        let Some(reply) = parse_usize_cell(table, row, "winning_second_reply_id", &context, report) else {
            continue;
        };
        let Some(reply_x) = parse_usize_cell(table, row, "reply_x", &context, report) else {
            continue;
        };
        let Some(reply_y) = parse_usize_cell(table, row, "reply_y", &context, report) else {
            continue;
        };

        if !ids.insert(first) {
            report.issues.push(format!("{context}: duplicate first_id {first}"));
        }
        if first != first_y * board.size() + first_x {
            report.issues.push(format!("{context}: first id and coordinates disagree"));
        }
        if reply != reply_y * board.size() + reply_x {
            report.issues.push(format!("{context}: reply id and coordinates disagree"));
        }
        if cell(table, row, "result_for_first_player") != Some("LOSS") {
            report.issues.push(format!("{context}: expected result LOSS"));
        }
        match board.transform_point(first, transform) {
            Ok(actual_rep) if actual_rep == representative => {}
            Ok(actual_rep) => report.issues.push(format!(
                "{context}: transform {transform} maps first move to {actual_rep}, not {representative}"
            )),
            Err(e) => report.issues.push(format!("{context}: {e}")),
        }
        if let Some(&rep_reply) = representative_reply.get(&representative) {
            match board.inverse_transform_point(rep_reply, transform) {
                Ok(expected_reply) if expected_reply == reply => {}
                Ok(expected_reply) => report.issues.push(format!(
                    "{context}: symmetry implies reply {expected_reply}, file contains {reply}"
                )),
                Err(e) => report.issues.push(format!("{context}: {e}")),
            }
        } else {
            report.issues.push(format!(
                "{context}: representative {representative} is absent from classification"
            ));
        }
    }

    for id in 0..board.point_count() {
        if !ids.contains(&id) {
            report.issues.push(format!("all-first-moves table is missing first_id {id}"));
        }
    }
}
