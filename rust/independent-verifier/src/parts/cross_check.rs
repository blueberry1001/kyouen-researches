mod cross_check_impl {
    use std::collections::{BTreeMap, HashSet};
    use std::io::{BufRead, BufReader, Write};
    use std::path::{Path, PathBuf};
    use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};

    use super::{bit, ids_from_mask, BoardSpec, Mask, Outcome, SolveOptions, Solver};

    #[derive(Clone, Debug)]
    pub struct CrossCheckOptions {
        pub cpp_path: PathBuf,
        pub size: usize,
        pub samples: usize,
        pub seed: u64,
        pub max_stones: usize,
        pub solve_max_size: usize,
        pub node_limit: Option<u64>,
    }

    #[derive(Clone, Debug, Default)]
    pub struct CrossCheckReport {
        pub valid_samples: usize,
        pub invalid_samples: usize,
        pub solved_samples: usize,
        pub witness_checks: usize,
    }

    #[derive(Clone, Debug)]
    struct CppReply {
        valid: bool,
        legal: Vec<usize>,
        forbidden: Vec<usize>,
        canonical: Vec<usize>,
        transforms: [Vec<usize>; 8],
        forbidden_quadruples: u64,
        outcome: Option<Outcome>,
        winning_move: Option<usize>,
    }

    struct CppServer {
        child: Child,
        stdin: ChildStdin,
        stdout: BufReader<ChildStdout>,
    }

    impl CppServer {
        fn start(path: &Path, options: &CrossCheckOptions, solve: bool) -> Result<Self, String> {
            let mut command = Command::new(path);
            command
                .arg("--size")
                .arg(options.size.to_string())
                .arg("--serve")
                .arg("--format")
                .arg("kv")
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::inherit());
            if solve {
                command.arg("--solve");
                if let Some(limit) = options.node_limit {
                    command.arg("--node-limit").arg(limit.to_string());
                }
            }
            let mut child = command
                .spawn()
                .map_err(|e| format!("failed to start C++ query tool {:?}: {e}", path))?;
            let stdin = child
                .stdin
                .take()
                .ok_or_else(|| "failed to open C++ query stdin".to_string())?;
            let stdout = child
                .stdout
                .take()
                .ok_or_else(|| "failed to open C++ query stdout".to_string())?;
            Ok(Self {
                child,
                stdin,
                stdout: BufReader::new(stdout),
            })
        }

        fn query(&mut self, state: Mask) -> Result<CppReply, String> {
            let ids = ids_from_mask(state);
            for (index, id) in ids.iter().enumerate() {
                if index != 0 {
                    write!(self.stdin, ",").map_err(|e| e.to_string())?;
                }
                write!(self.stdin, "{id}").map_err(|e| e.to_string())?;
            }
            writeln!(self.stdin).map_err(|e| e.to_string())?;
            self.stdin.flush().map_err(|e| e.to_string())?;

            let mut line = String::new();
            let bytes = self
                .stdout
                .read_line(&mut line)
                .map_err(|e| format!("failed to read C++ response: {e}"))?;
            if bytes == 0 {
                return Err("C++ query tool exited before returning a response".into());
            }
            parse_reply(line.trim_end())
        }

        fn finish(mut self) -> Result<(), String> {
            drop(self.stdin);
            let status = self
                .child
                .wait()
                .map_err(|e| format!("failed to wait for C++ query tool: {e}"))?;
            if status.success() {
                Ok(())
            } else {
                Err(format!("C++ query tool exited with {status}"))
            }
        }
    }

    pub fn cross_check_cpp(options: &CrossCheckOptions) -> Result<CrossCheckReport, String> {
        if options.samples == 0 {
            return Err("--samples must be positive".into());
        }
        let board = BoardSpec::new(options.size).map_err(|e| e.to_string())?;
        let solve = options.size <= options.solve_max_size;
        let mut server = CppServer::start(&options.cpp_path, options, solve)?;
        let result = run_cross_check(&board, &mut server, options, solve);
        let finish_result = server.finish();
        match (result, finish_result) {
            (Ok(report), Ok(())) => Ok(report),
            (Err(e), _) => Err(e),
            (Ok(_), Err(e)) => Err(e),
        }
    }

    fn run_cross_check(
        board: &BoardSpec,
        server: &mut CppServer,
        options: &CrossCheckOptions,
        solve: bool,
    ) -> Result<CrossCheckReport, String> {
        let samples = generate_samples(board, options.samples, options.seed, options.max_stones)?;
        let mut report = CrossCheckReport::default();

        for (sample_index, state) in samples.into_iter().enumerate() {
            let reply = server.query(state)?;
            compare_structure(board, state, &reply, sample_index)?;
            report.valid_samples += 1;

            if solve {
                compare_outcome(board, state, &reply, server, options, sample_index, &mut report)?;
            }
        }

        if board.size() >= 2 {
            let invalid = board
                .mask_from_ids([
                    board.point_id(0, 0).map_err(|e| e.to_string())?,
                    board.point_id(1, 0).map_err(|e| e.to_string())?,
                    board.point_id(0, 1).map_err(|e| e.to_string())?,
                    board.point_id(1, 1).map_err(|e| e.to_string())?,
                ])
                .map_err(|e| e.to_string())?;
            if board.is_valid_position(invalid).map_err(|e| e.to_string())? {
                return Err("Rust unexpectedly accepted the unit-square forbidden quadruple".into());
            }
            let reply = server.query(invalid)?;
            if reply.valid {
                return Err("C++ unexpectedly accepted the unit-square forbidden quadruple".into());
            }
            report.invalid_samples += 1;
        }

        Ok(report)
    }

    fn compare_structure(
        board: &BoardSpec,
        state: Mask,
        reply: &CppReply,
        sample_index: usize,
    ) -> Result<(), String> {
        let context = || format!("sample {sample_index}, state {:?}", ids_from_mask(state));
        if !reply.valid {
            return Err(format!("C++ rejected a Rust-generated valid {}", context()));
        }
        if !board.is_valid_position(state).map_err(|e| e.to_string())? {
            return Err(format!("Rust generated an invalid {}", context()));
        }
        let rust_legal = board.legal_mask(state).map_err(|e| e.to_string())?;
        compare_ids("legal moves", &ids_from_mask(rust_legal), &reply.legal, &context())?;

        let rust_forbidden = board.full_mask() & !state & !rust_legal;
        compare_ids(
            "forbidden empty points",
            &ids_from_mask(rust_forbidden),
            &reply.forbidden,
            &context(),
        )?;

        compare_ids(
            "canonical state",
            &ids_from_mask(board.canonical(state)),
            &reply.canonical,
            &context(),
        )?;

        for transform in 0..8 {
            let transformed = board
                .transform_mask(state, transform)
                .map_err(|e| e.to_string())?;
            compare_ids(
                &format!("transform {transform}"),
                &ids_from_mask(transformed),
                &reply.transforms[transform],
                &context(),
            )?;
        }

        if reply.forbidden_quadruples != board.forbidden_quadruples() {
            return Err(format!(
                "forbidden quadruple count mismatch for {}: Rust={}, C++={}",
                context(),
                board.forbidden_quadruples(),
                reply.forbidden_quadruples
            ));
        }
        Ok(())
    }

    fn compare_outcome(
        board: &BoardSpec,
        state: Mask,
        reply: &CppReply,
        server: &mut CppServer,
        options: &CrossCheckOptions,
        sample_index: usize,
        report: &mut CrossCheckReport,
    ) -> Result<(), String> {
        let mut solver = Solver::new(
            board,
            SolveOptions {
                use_symmetry: true,
                node_limit: options.node_limit,
            },
        );
        let rust_outcome = solver
            .solve(state)
            .map_err(|e| format!("Rust solve failed for sample {sample_index}: {e}"))?;
        let cpp_outcome = reply
            .outcome
            .ok_or_else(|| format!("C++ omitted outcome for solved sample {sample_index}"))?;
        if rust_outcome != cpp_outcome {
            return Err(format!(
                "outcome mismatch for sample {sample_index}, state {:?}: Rust={rust_outcome}, C++={cpp_outcome}",
                ids_from_mask(state)
            ));
        }
        report.solved_samples += 1;

        match rust_outcome {
            Outcome::Losing => {
                if reply.winning_move.is_some() {
                    return Err(format!(
                        "C++ supplied a winning move for losing sample {sample_index}"
                    ));
                }
                if solver.winning_move(state).map_err(|e| e.to_string())?.is_some() {
                    return Err(format!(
                        "Rust supplied a winning move for losing sample {sample_index}"
                    ));
                }
            }
            Outcome::Winning => {
                let cpp_move = reply
                    .winning_move
                    .ok_or_else(|| format!("C++ omitted a winning move for sample {sample_index}"))?;
                let legal = board.legal_mask(state).map_err(|e| e.to_string())?;
                if cpp_move >= board.point_count() || legal & bit(cpp_move) == 0 {
                    return Err(format!(
                        "C++ winning move {cpp_move} is illegal for sample {sample_index}"
                    ));
                }
                let cpp_child = solver
                    .solve(state | bit(cpp_move))
                    .map_err(|e| e.to_string())?;
                if cpp_child != Outcome::Losing {
                    return Err(format!(
                        "C++ winning move {cpp_move} does not lead to LOSS in Rust for sample {sample_index}"
                    ));
                }
                report.witness_checks += 1;

                let rust_move = solver
                    .winning_move(state)
                    .map_err(|e| e.to_string())?
                    .ok_or_else(|| format!("Rust omitted a winning move for sample {sample_index}"))?;
                let cpp_child_reply = server.query(state | bit(rust_move))?;
                if cpp_child_reply.outcome != Some(Outcome::Losing) {
                    return Err(format!(
                        "Rust winning move {rust_move} does not lead to LOSS in C++ for sample {sample_index}"
                    ));
                }
                report.witness_checks += 1;
            }
        }
        Ok(())
    }

    fn compare_ids(
        label: &str,
        rust: &[usize],
        cpp: &[usize],
        context: &str,
    ) -> Result<(), String> {
        if rust == cpp {
            Ok(())
        } else {
            Err(format!(
                "{label} mismatch for {context}: Rust={rust:?}, C++={cpp:?}"
            ))
        }
    }

    fn generate_samples(
        board: &BoardSpec,
        requested: usize,
        seed: u64,
        max_stones: usize,
    ) -> Result<Vec<Mask>, String> {
        let max_stones = max_stones.min(board.point_count());
        let mut rng = XorShift64::new(seed);
        let mut seen = HashSet::new();
        let mut samples = Vec::with_capacity(requested);
        seen.insert(0);
        samples.push(0);

        let max_attempts = requested.saturating_mul(200).max(200);
        for _ in 0..max_attempts {
            if samples.len() >= requested {
                break;
            }
            let target = if max_stones == 0 {
                0
            } else {
                (rng.next() as usize) % (max_stones + 1)
            };
            let mut state = 0;
            for _ in 0..target {
                let legal = board.legal_mask(state).map_err(|e| e.to_string())?;
                let moves = ids_from_mask(legal);
                if moves.is_empty() {
                    break;
                }
                let point = moves[(rng.next() as usize) % moves.len()];
                state |= bit(point);
            }
            if seen.insert(state) {
                samples.push(state);
            }
        }
        if samples.len() != requested {
            return Err(format!(
                "could only generate {} distinct valid samples out of {requested}; increase --max-stones",
                samples.len()
            ));
        }
        Ok(samples)
    }

    struct XorShift64(u64);

    impl XorShift64 {
        fn new(seed: u64) -> Self {
            Self(if seed == 0 { 0x9e3779b97f4a7c15 } else { seed })
        }

        fn next(&mut self) -> u64 {
            let mut x = self.0;
            x ^= x << 13;
            x ^= x >> 7;
            x ^= x << 17;
            self.0 = x;
            x
        }
    }

    fn parse_reply(line: &str) -> Result<CppReply, String> {
        let mut fields = BTreeMap::new();
        for field in line.split(';') {
            let Some((key, value)) = field.split_once('=') else {
                return Err(format!("malformed C++ field {field:?}"));
            };
            fields.insert(key, value);
        }
        if let Some(error) = fields.get("error") {
            return Err(format!("C++ query error: {error}"));
        }
        let mut transform_values = Vec::with_capacity(8);
        for index in 0..8 {
            let key = format!("t{index}");
            let value = fields
                .get(key.as_str())
                .copied()
                .ok_or_else(|| format!("C++ response omitted {key}: {line}"))?;
            transform_values.push(parse_ids(value)?);
        }
        let transforms: [Vec<usize>; 8] = transform_values
            .try_into()
            .map_err(|_| "internal transform-array conversion failed".to_string())?;
        let outcome = match required(&fields, "outcome")? {
            "NA" | "INVALID" => None,
            "WIN" => Some(Outcome::Winning),
            "LOSS" => Some(Outcome::Losing),
            other => return Err(format!("unknown C++ outcome {other:?}")),
        };
        let winning_move = match required(&fields, "winning_move")? {
            "NA" => None,
            value => Some(
                value
                    .parse()
                    .map_err(|_| format!("invalid C++ winning_move {value:?}"))?,
            ),
        };
        Ok(CppReply {
            valid: match required(&fields, "valid")? {
                "1" => true,
                "0" => false,
                value => return Err(format!("invalid C++ valid value {value:?}")),
            },
            legal: parse_ids(required(&fields, "legal")?)?,
            forbidden: parse_ids(required(&fields, "forbidden")?)?,
            canonical: parse_ids(required(&fields, "canonical")?)?,
            transforms,
            forbidden_quadruples: required(&fields, "forbidden_quadruples")?
                .parse()
                .map_err(|_| "invalid forbidden_quadruples value".to_string())?,
            outcome,
            winning_move,
        })
    }

    fn required<'a>(fields: &'a BTreeMap<&str, &str>, key: &str) -> Result<&'a str, String> {
        fields
            .get(key)
            .copied()
            .ok_or_else(|| format!("C++ response omitted {key}"))
    }

    fn parse_ids(value: &str) -> Result<Vec<usize>, String> {
        if value.is_empty() {
            return Ok(Vec::new());
        }
        value
            .split(',')
            .map(|part| {
                part.parse::<usize>()
                    .map_err(|_| format!("invalid point id {part:?} in C++ response"))
            })
            .collect()
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn parses_cpp_kv_reply() {
            let reply = parse_reply(
                "valid=1;legal=2,3;forbidden=5;canonical=0,1;t0=0,1;t1=2,3;t2=4,5;t3=6,7;t4=0,1;t5=2,3;t6=4,5;t7=6,7;forbidden_quadruples=194;outcome=WIN;winning_move=2;visited=10",
            )
            .unwrap();
            assert!(reply.valid);
            assert_eq!(reply.legal, vec![2, 3]);
            assert_eq!(reply.forbidden, vec![5]);
            assert_eq!(reply.outcome, Some(Outcome::Winning));
            assert_eq!(reply.winning_move, Some(2));
        }

        #[test]
        fn sample_generation_is_deterministic_and_valid() {
            let board = BoardSpec::new(5).unwrap();
            let a = generate_samples(&board, 20, 123, 8).unwrap();
            let b = generate_samples(&board, 20, 123, 8).unwrap();
            assert_eq!(a, b);
            assert!(a
                .into_iter()
                .all(|state| board.is_valid_position(state).unwrap()));
        }
    }
}

pub use cross_check_impl::{cross_check_cpp, CrossCheckOptions, CrossCheckReport};
