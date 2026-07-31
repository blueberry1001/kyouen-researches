fn audit_child_proof(board: &BoardSpec, name: &str, table: &CsvTable, report: &mut AuditReport) {
    let Some((first, reply, representatives)) = parse_child_filename(name) else {
        report.issues.push(format!("cannot parse proof filename {name}"));
        return;
    };
    let third_column = if table.header_index.contains_key("third") {
        "third"
    } else {
        "third_id"
    };
    let mut thirds = HashSet::new();
    for (row_index, row) in table.rows.iter().enumerate() {
        report.checked_rows += 1;
        let context = format!("{name} row {}", row_index + 2);
        let Some(third) = parse_usize_cell(table, row, third_column, &context, report) else {
            continue;
        };
        let Some(x) = parse_usize_cell(table, row, "x", &context, report) else {
            continue;
        };
        let Some(y) = parse_usize_cell(table, row, "y", &context, report) else {
            continue;
        };
        if third != y * board.size() + x {
            report.issues.push(format!("{context}: third id and coordinates disagree"));
        }
        if third == first || third == reply {
            report.issues.push(format!("{context}: third move repeats an occupied point"));
        }
        if !thirds.insert(third) {
            report.issues.push(format!("{context}: duplicate third move {third}"));
        }
        if cell(table, row, "outcome") != Some("WIN") {
            report.issues.push(format!("{context}: expected outcome WIN"));
        }
        if let Some(state) = cell(table, row, "state") {
            let expected = format!("{first}-{reply}-{third}");
            if state != expected {
                report.issues.push(format!(
                    "{context}: state is {state:?}, expected {expected:?}"
                ));
            }
        }
    }

    let occupied = [first, reply];
    if representatives {
        let mut expected_orbits = HashSet::new();
        for third in 0..board.point_count() {
            if occupied.contains(&third) {
                continue;
            }
            let transposed = match board.transpose_point(third) {
                Ok(p) => p,
                Err(e) => {
                    report.issues.push(format!("{name}: {e}"));
                    return;
                }
            };
            expected_orbits.insert(third.min(transposed));
        }

        let mut actual_orbits = HashSet::new();
        for &third in &thirds {
            let transposed = match board.transpose_point(third) {
                Ok(p) => p,
                Err(e) => {
                    report.issues.push(format!("{name}: {e}"));
                    return;
                }
            };
            let orbit = third.min(transposed);
            if !actual_orbits.insert(orbit) {
                report.issues.push(format!(
                    "{name}: more than one representative was recorded for transpose orbit {orbit}"
                ));
            }
        }
        if actual_orbits != expected_orbits {
            report.issues.push(format!(
                "{name}: representative rows cover {} transpose orbits; expected {}",
                actual_orbits.len(),
                expected_orbits.len()
            ));
        }
    } else {
        let expected: HashSet<usize> = (0..board.point_count())
            .filter(|p| !occupied.contains(p))
            .collect();
        if thirds != expected {
            report.issues.push(format!(
                "{name}: third-move set has {} entries; expected all {} legal empty points",
                thirds.len(),
                expected.len()
            ));
        }
    }
}

fn parse_child_filename(name: &str) -> Option<(usize, usize, bool)> {
    let rest = name.strip_prefix("10x10-children-")?;
    let mut parts = rest.split('-');
    let first = parts.next()?.parse().ok()?;
    let reply = parts.next()?.parse().ok()?;
    let representatives = name.ends_with("-representatives.csv");
    Some((first, reply, representatives))
}

#[derive(Debug, Clone)]
struct CsvTable {
    header_index: HashMap<String, usize>,
    rows: Vec<Vec<String>>,
}

fn read_csv_table(path: &Path) -> Result<CsvTable, String> {
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let mut lines = text.lines();
    let header_line = lines.next().ok_or_else(|| "empty CSV".to_string())?;
    let headers = parse_csv_line(header_line)?;
    let header_index = headers
        .iter()
        .enumerate()
        .map(|(i, h)| (h.clone(), i))
        .collect::<HashMap<_, _>>();
    let mut rows = Vec::new();
    for (line_number, line) in lines.enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let row = parse_csv_line(line).map_err(|e| format!("line {}: {e}", line_number + 2))?;
        if row.len() != headers.len() {
            return Err(format!(
                "line {} has {} cells; header has {}",
                line_number + 2,
                row.len(),
                headers.len()
            ));
        }
        rows.push(row);
    }
    Ok(CsvTable {
        header_index,
        rows,
    })
}

fn parse_csv_line(line: &str) -> Result<Vec<String>, String> {
    let mut cells = Vec::new();
    let mut current = String::new();
    let mut chars = line.chars().peekable();
    let mut quoted = false;
    while let Some(ch) = chars.next() {
        if quoted {
            if ch == '"' {
                if chars.peek() == Some(&'"') {
                    chars.next();
                    current.push('"');
                } else {
                    quoted = false;
                }
            } else {
                current.push(ch);
            }
        } else {
            match ch {
                '"' if current.is_empty() => quoted = true,
                ',' => {
                    cells.push(std::mem::take(&mut current));
                }
                _ => current.push(ch),
            }
        }
    }
    if quoted {
        return Err("unterminated quoted field".into());
    }
    cells.push(current);
    Ok(cells)
}

fn cell<'a>(table: &'a CsvTable, row: &'a [String], header: &str) -> Option<&'a str> {
    let index = *table.header_index.get(header)?;
    row.get(index).map(String::as_str)
}

fn parse_usize_cell(
    table: &CsvTable,
    row: &[String],
    header: &str,
    context: &str,
    report: &mut AuditReport,
) -> Option<usize> {
    let Some(value) = cell(table, row, header) else {
        report.issues.push(format!("{context}: missing column {header}"));
        return None;
    };
    match value.parse::<usize>() {
        Ok(parsed) => Some(parsed),
        Err(_) => {
            report
                .issues
                .push(format!("{context}: {header} is not an integer: {value:?}"));
            None
        }
    }
}
