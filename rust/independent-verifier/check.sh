#!/usr/bin/env sh
set -eu
cargo test --release
cargo run --release -- self-test
cargo run --release -- audit-evidence evidence-sample
