use std::env;
use std::path::Path;
use std::process::ExitCode;

use kyouen_verifier::{
    audit_evidence_dir, classify_first_moves, run_reference_self_test, BoardSpec,
    SolveOptions, Solver,
};

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("error: {message}");
            ExitCode::from(1)
        }
    }
}

fn run() -> Result<(), String> {
    let mut args = env::args().skip(1);
    let Some(command) = args.next() else {
        print_usage();
        return Ok(());
    };

    match command.as_str() {
        "solve" => command_solve(args.collect()),
        "classify-first" => command_classify(args.collect()),
        "audit-evidence" => command_audit(args.collect()),
        "self-test" => command_self_test(args.collect()),
        "help" | "--help" | "-h" => {
            print_usage();
            Ok(())
        }
        other => Err(format!("unknown command {other:?}")),
    }
}

fn command_solve(args: Vec<String>) -> Result<(), String> {
    let parsed = CommonArgs::parse(&args)?;
    let board = BoardSpec::new(parsed.size).map_err(|e| e.to_string())?;
    let occupied = parse_state(&board, parsed.ids.as_deref(), parsed.coords.as_deref())?;
    let mut solver = Solver::new(
        &board,
        SolveOptions {
            use_symmetry: !parsed.no_symmetry,
            node_limit: parsed.node_limit,
        },
    );
    let outcome = solver.solve(occupied).map_err(|e| e.to_string())?;
    let winning_move = solver.winning_move(occupied).map_err(|e| e.to_string())?;
    println!("outcome={outcome}");
    match winning_move {
        Some(id) => {
            let (x, y) = board.coordinates(id).map_err(|e| e.to_string())?;
            println!("winning_move_id={id}");
            println!("winning_move=({x},{y})");
        }
        None => println!("winning_move=none"),
    }
    let stats = solver.stats();
    println!("visited={}", stats.visited);
    println!("memo_hits={}", stats.memo_hits);
    println!("memo_entries={}", solver.memo_len());
    println!("symmetry_duplicates={}", stats.symmetry_duplicates);
    println!("max_stones={}", stats.max_stones);
    println!("forbidden_quadruples={}", board.forbidden_quadruples());
    Ok(())
}

fn command_classify(args: Vec<String>) -> Result<(), String> {
    let parsed = CommonArgs::parse(&args)?;
    if parsed.ids.is_some() || parsed.coords.is_some() {
        return Err("classify-first does not accept --ids or --coords".into());
    }
    let board = BoardSpec::new(parsed.size).map_err(|e| e.to_string())?;
    let rows = classify_first_moves(
        &board,
        SolveOptions {
            use_symmetry: !parsed.no_symmetry,
            node_limit: parsed.node_limit,
        },
    )
    .map_err(|e| e.to_string())?;

    println!("first_id,first_x,first_y,result_for_first_player,winning_reply_id,reply_x,reply_y");
    for row in rows {
        let (x, y) = board.coordinates(row.point).map_err(|e| e.to_string())?;
        match row.winning_reply {
            Some(reply) => {
                let (rx, ry) = board.coordinates(reply).map_err(|e| e.to_string())?;
                println!(
                    "{},{},{},{},{},{},{}",
                    row.point, x, y, row.result_for_first_player, reply, rx, ry
                );
            }
            None => println!(
                "{},{},{},{},,,",
                row.point, x, y, row.result_for_first_player
            ),
        }
    }
    Ok(())
}

fn command_audit(args: Vec<String>) -> Result<(), String> {
    if args.len() != 1 {
        return Err("usage: kyouen-verifier audit-evidence PATH".into());
    }
    let report = audit_evidence_dir(Path::new(&args[0])).map_err(|e| e.to_string())?;
    println!("checked_files={}", report.checked_files);
    println!("checked_rows={}", report.checked_rows);
    println!("issues={}", report.issues.len());
    for issue in &report.issues {
        println!("ISSUE: {issue}");
    }
    if report.is_ok() {
        println!("audit=OK");
        Ok(())
    } else {
        Err("evidence audit found inconsistencies".into())
    }
}

fn command_self_test(args: Vec<String>) -> Result<(), String> {
    if !args.is_empty() {
        return Err("self-test takes no arguments".into());
    }
    for message in run_reference_self_test()? {
        println!("{message}");
    }
    println!("self_test=OK");
    Ok(())
}

#[derive(Debug, Default)]
struct CommonArgs {
    size: usize,
    ids: Option<String>,
    coords: Option<String>,
    no_symmetry: bool,
    node_limit: Option<u64>,
}

impl CommonArgs {
    fn parse(args: &[String]) -> Result<Self, String> {
        let mut result = CommonArgs {
            size: 0,
            ..CommonArgs::default()
        };
        let mut i = 0usize;
        while i < args.len() {
            match args[i].as_str() {
                "--size" => {
                    i += 1;
                    result.size = parse_next(args, i, "--size")?
                        .parse()
                        .map_err(|_| "--size must be a positive integer".to_string())?;
                }
                "--ids" => {
                    i += 1;
                    result.ids = Some(parse_next(args, i, "--ids")?.to_string());
                }
                "--coords" => {
                    i += 1;
                    result.coords = Some(parse_next(args, i, "--coords")?.to_string());
                }
                "--no-symmetry" => result.no_symmetry = true,
                "--node-limit" => {
                    i += 1;
                    result.node_limit = Some(
                        parse_next(args, i, "--node-limit")?
                            .parse()
                            .map_err(|_| "--node-limit must be an integer".to_string())?,
                    );
                }
                other => return Err(format!("unknown option {other:?}")),
            }
            i += 1;
        }
        if result.size == 0 {
            return Err("--size is required".into());
        }
        if result.ids.is_some() && result.coords.is_some() {
            return Err("use either --ids or --coords, not both".into());
        }
        Ok(result)
    }
}

fn parse_next<'a>(args: &'a [String], index: usize, option: &str) -> Result<&'a str, String> {
    args.get(index)
        .map(String::as_str)
        .ok_or_else(|| format!("{option} requires a value"))
}

fn parse_state(
    board: &BoardSpec,
    ids: Option<&str>,
    coords: Option<&str>,
) -> Result<u128, String> {
    if let Some(ids) = ids {
        let parsed = if ids.trim().is_empty() {
            Vec::new()
        } else {
            ids.split(',')
                .map(|part| {
                    part.trim()
                        .parse::<usize>()
                        .map_err(|_| format!("invalid point id {part:?}"))
                })
                .collect::<Result<Vec<_>, _>>()?
        };
        return board.mask_from_ids(parsed).map_err(|e| e.to_string());
    }
    if let Some(coords) = coords {
        let mut parsed = Vec::new();
        if !coords.trim().is_empty() {
            for pair in coords.split(';') {
                let mut xy = pair.split(',');
                let x = xy
                    .next()
                    .ok_or_else(|| format!("invalid coordinate {pair:?}"))?
                    .trim()
                    .parse::<usize>()
                    .map_err(|_| format!("invalid x coordinate in {pair:?}"))?;
                let y = xy
                    .next()
                    .ok_or_else(|| format!("invalid coordinate {pair:?}"))?
                    .trim()
                    .parse::<usize>()
                    .map_err(|_| format!("invalid y coordinate in {pair:?}"))?;
                if xy.next().is_some() {
                    return Err(format!("invalid coordinate {pair:?}"));
                }
                parsed.push(board.point_id(x, y).map_err(|e| e.to_string())?);
            }
        }
        return board.mask_from_ids(parsed).map_err(|e| e.to_string());
    }
    Ok(0)
}

fn print_usage() {
    println!(
        "kyouen-verifier\n\n\
Commands:\n\
  solve --size N [--ids 1,2,3 | --coords '0,0;1,2'] [--node-limit N] [--no-symmetry]\n\
  classify-first --size N [--node-limit N] [--no-symmetry]\n\
  audit-evidence PATH\n\
  self-test\n\n\
Outcome is always from the point of view of the player whose turn it is.\n\
The reference solver is intentionally simple and is not intended to redo the\n\
full 10x10 search in one run."
    );
}
