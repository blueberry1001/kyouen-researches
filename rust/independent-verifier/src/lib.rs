//! Independent reference implementation for the Kyouen game.
//!
//! The optimized C++ solver keeps an incrementally updated legal-move mask.
//! This implementation deliberately takes a different route: for every state,
//! it reconstructs all forbidden points from the occupied set. It is slower,
//! but the different structure makes it useful for independent checking.

use std::collections::{HashMap, HashSet};
use std::fmt;
use std::fs;
use std::path::{Path, PathBuf};

include!("parts/board.rs");
include!("parts/solver.rs");
include!("parts/cross_check.rs");
include!("parts/certificate.rs");
include!("parts/audit_entry.rs");
include!("parts/audit_classification.rs");
include!("parts/audit_children.rs");
include!("parts/self_test.rs");
include!("parts/tests.rs");
