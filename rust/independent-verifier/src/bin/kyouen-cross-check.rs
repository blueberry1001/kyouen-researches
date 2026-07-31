use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

use kyouen_verifier::{cross_check_cpp, CrossCheckOptions};

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
    let args = env::args().skip(1).collect::<Vec<_>>();
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        print_usage();
        return Ok(());
    }

    let mut cpp_path = None;
    let mut size = None;
    let mut samples = 100usize;
    let mut seed = 1u64;
    let mut max_stones = 12usize;
    let mut solve_max_size = 5usize;
    let mut node_limit = Some(20_000_000u64);

    let mut index = 0usize;
    while index < args.len() {
        match args[index].as_str() {
            "--cpp" => {
                index += 1;
                cpp_path = Some(PathBuf::from(value(&args, index, "--cpp")?));
            }
            "--size" => {
                index += 1;
                size = Some(parse(value(&args, index, "--size")?, "--size")?);
            }
            "--samples" => {
                index += 1;
                samples = parse(value(&args, index, "--samples")?, "--samples")?;
            }
            "--seed" => {
                index += 1;
                seed = parse(value(&args, index, "--seed")?, "--seed")?;
            }
            "--max-stones" => {
                index += 1;
                max_stones = parse(value(&args, index, "--max-stones")?, "--max-stones")?;
            }
            "--solve-max-size" => {
                index += 1;
                solve_max_size = parse(
                    value(&args, index, "--solve-max-size")?,
                    "--solve-max-size",
                )?;
            }
            "--node-limit" => {
                index += 1;
                node_limit = Some(parse(
                    value(&args, index, "--node-limit")?,
                    "--node-limit",
                )?);
            }
            "--no-node-limit" => node_limit = None,
            other => return Err(format!("unknown option {other:?}")),
        }
        index += 1;
    }

    let options = CrossCheckOptions {
        cpp_path: cpp_path.ok_or_else(|| "--cpp is required".to_string())?,
        size: size.ok_or_else(|| "--size is required".to_string())?,
        samples,
        seed,
        max_stones,
        solve_max_size,
        node_limit,
    };
    let report = cross_check_cpp(&options)?;
    println!("size={}", options.size);
    println!("valid_samples={}", report.valid_samples);
    println!("invalid_samples={}", report.invalid_samples);
    println!("solved_samples={}", report.solved_samples);
    println!("witness_checks={}", report.witness_checks);
    println!("cross_check=OK");
    Ok(())
}

fn value<'a>(args: &'a [String], index: usize, option: &str) -> Result<&'a str, String> {
    args.get(index)
        .map(String::as_str)
        .ok_or_else(|| format!("{option} requires a value"))
}

fn parse<T>(value: &str, option: &str) -> Result<T, String>
where
    T: std::str::FromStr,
{
    value
        .parse()
        .map_err(|_| format!("{option} has an invalid value {value:?}"))
}

fn print_usage() {
    println!(
        "kyouen-cross-check\n\n\
Usage:\n\
  cargo run --release --bin kyouen-cross-check -- \\\n    --cpp /path/to/kyouen-query --size N [options]\n\n\
Options:\n\
  --samples N          Number of deterministic valid random-walk states (default: 100)\n\
  --seed N             Xorshift seed (default: 1)\n\
  --max-stones N       Maximum stones in generated states (default: 12)\n\
  --solve-max-size N   Compare WIN/LOSS when board size is at most N (default: 5)\n\
  --node-limit N       Per-position node limit for both solvers (default: 20000000)\n\
  --no-node-limit      Disable the per-position node limit\n\n\
For larger boards, the checker compares validity, legal and forbidden points,\n\
all eight symmetries, canonicalization, and the forbidden-quadruple count."
    );
}
