#[derive(Clone, Debug)]
pub struct SolveOptions {
    pub use_symmetry: bool,
    pub node_limit: Option<u64>,
}

impl Default for SolveOptions {
    fn default() -> Self {
        Self {
            use_symmetry: true,
            node_limit: None,
        }
    }
}

#[derive(Clone, Debug, Default)]
pub struct SolveStats {
    pub visited: u64,
    pub memo_hits: u64,
    pub symmetry_duplicates: u64,
    pub max_stones: usize,
}

#[derive(Debug, Clone)]
pub enum SolveError {
    Board(BoardError),
    InvalidPosition,
    NodeLimitExceeded { limit: u64 },
}

impl fmt::Display for SolveError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SolveError::Board(e) => write!(f, "{e}"),
            SolveError::InvalidPosition => write!(f, "the supplied state already contains a forbidden quadruple"),
            SolveError::NodeLimitExceeded { limit } => {
                write!(f, "node limit {limit} exceeded before the outcome was proved")
            }
        }
    }
}

impl std::error::Error for SolveError {}

impl From<BoardError> for SolveError {
    fn from(value: BoardError) -> Self {
        SolveError::Board(value)
    }
}

pub struct Solver<'a> {
    board: &'a BoardSpec,
    options: SolveOptions,
    memo: HashMap<Mask, Outcome>,
    stats: SolveStats,
}

impl<'a> Solver<'a> {
    pub fn new(board: &'a BoardSpec, options: SolveOptions) -> Self {
        Self {
            board,
            options,
            memo: HashMap::new(),
            stats: SolveStats::default(),
        }
    }

    pub fn solve(&mut self, occupied: Mask) -> Result<Outcome, SolveError> {
        if !self.board.is_valid_position(occupied)? {
            return Err(SolveError::InvalidPosition);
        }
        self.solve_inner(occupied)
    }

    pub fn winning_move(&mut self, occupied: Mask) -> Result<Option<usize>, SolveError> {
        if self.solve(occupied)? == Outcome::Losing {
            return Ok(None);
        }
        let legal = self.board.legal_mask(occupied)?;
        let mut moves = ids_from_mask(legal);
        moves.sort_by_key(|&mv| {
            self.board
                .legal_mask(occupied | bit(mv))
                .map(|m| m.count_ones())
                .unwrap_or(u32::MAX)
        });
        for mv in moves {
            if self.solve_inner(occupied | bit(mv))? == Outcome::Losing {
                return Ok(Some(mv));
            }
        }
        Ok(None)
    }

    pub fn stats(&self) -> &SolveStats {
        &self.stats
    }

    pub fn memo_len(&self) -> usize {
        self.memo.len()
    }

    fn key(&self, occupied: Mask) -> Mask {
        if self.options.use_symmetry {
            self.board.canonical(occupied)
        } else {
            occupied
        }
    }

    fn solve_inner(&mut self, occupied: Mask) -> Result<Outcome, SolveError> {
        let key = self.key(occupied);
        if let Some(&outcome) = self.memo.get(&key) {
            self.stats.memo_hits += 1;
            return Ok(outcome);
        }

        if let Some(limit) = self.options.node_limit {
            if self.stats.visited >= limit {
                return Err(SolveError::NodeLimitExceeded { limit });
            }
        }
        self.stats.visited += 1;
        self.stats.max_stones = self.stats.max_stones.max(occupied.count_ones() as usize);

        let legal = self.board.legal_mask(occupied)?;
        if legal == 0 {
            self.memo.insert(key, Outcome::Losing);
            return Ok(Outcome::Losing);
        }

        let mut children = Vec::new();
        let mut seen = HashSet::new();
        for mv in ids_from_mask(legal) {
            let child = occupied | bit(mv);
            let child_key = self.key(child);
            if !seen.insert(child_key) {
                self.stats.symmetry_duplicates += 1;
                continue;
            }
            let child_legal_count = self.board.legal_mask(child)?.count_ones();
            children.push((child_legal_count, child_key, child));
        }
        children.sort_unstable_by_key(|&(count, child_key, _)| (count, child_key));

        for (_, _, child) in children {
            if self.solve_inner(child)? == Outcome::Losing {
                self.memo.insert(key, Outcome::Winning);
                return Ok(Outcome::Winning);
            }
        }
        self.memo.insert(key, Outcome::Losing);
        Ok(Outcome::Losing)
    }
}

#[derive(Debug, Clone)]
pub struct FirstMoveResult {
    pub point: usize,
    pub result_for_first_player: Outcome,
    pub winning_reply: Option<usize>,
}

pub fn classify_first_moves(
    board: &BoardSpec,
    options: SolveOptions,
) -> Result<Vec<FirstMoveResult>, SolveError> {
    let mut solver = Solver::new(board, options);
    let mut rows = Vec::with_capacity(board.point_count());
    for first in 0..board.point_count() {
        let state = bit(first);
        let result_for_second = solver.solve(state)?;
        let result_for_first_player = match result_for_second {
            Outcome::Losing => Outcome::Winning,
            Outcome::Winning => Outcome::Losing,
        };
        let winning_reply = if result_for_first_player == Outcome::Losing {
            solver.winning_move(state)?
        } else {
            None
        };
        rows.push(FirstMoveResult {
            point: first,
            result_for_first_player,
            winning_reply,
        });
    }
    Ok(rows)
}
