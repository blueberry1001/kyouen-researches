use std::env;
use std::path::Path;
use std::process::ExitCode;

use kyouen_verifier::verify_certificate;

fn main() -> ExitCode {
    let mut args = env::args().skip(1);
    let Some(path) = args.next() else {
        eprintln!("usage: kyouen-cert-verify CERTIFICATE.cert");
        return ExitCode::from(2);
    };
    if args.next().is_some() {
        eprintln!("error: expected exactly one certificate path");
        return ExitCode::from(2);
    }

    match verify_certificate(Path::new(&path)) {
        Ok(report) => {
            println!("CERTIFICATE VALID");
            println!("format=KYOENC{}", report.format_version);
            println!("board={}x{}", report.board_size, report.board_size);
            println!("nodes={}", report.node_count);
            println!("losing_nodes={}", report.losing_nodes);
            println!("winning_nodes={}", report.winning_nodes);
            println!("forbidden_quadruples={}", report.forbidden_quadruples);
            println!("root_state=0x{:032x}", report.root_state);
            println!("root_stones={}", report.root_state.count_ones());
            println!("root_outcome={}", report.root_outcome);
            println!(
                "conclusion={}",
                if report.root_outcome.to_string() == "WIN" {
                    "PLAYER TO MOVE WINS"
                } else {
                    "PLAYER TO MOVE LOSES"
                }
            );
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::from(1)
        }
    }
}
