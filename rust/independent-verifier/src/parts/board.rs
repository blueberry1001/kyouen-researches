pub type Mask = u128;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Outcome {
    Losing,
    Winning,
}

impl fmt::Display for Outcome {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Outcome::Losing => write!(f, "LOSS"),
            Outcome::Winning => write!(f, "WIN"),
        }
    }
}

#[derive(Debug, Clone)]
pub struct BoardError(pub String);

impl fmt::Display for BoardError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for BoardError {}

#[derive(Clone, Debug)]
pub struct BoardSpec {
    size: usize,
    point_count: usize,
    full_mask: Mask,
    /// For a sorted triple (a,b,c), stores every d for which a,b,c,d
    /// are concyclic or collinear.
    completion: Vec<Mask>,
    symmetry_maps: Vec<Vec<usize>>,
    forbidden_quadruples: u64,
}

impl BoardSpec {
    pub fn new(size: usize) -> Result<Self, BoardError> {
        if size == 0 {
            return Err(BoardError("board size must be positive".into()));
        }
        let point_count = size
            .checked_mul(size)
            .ok_or_else(|| BoardError("board size overflow".into()))?;
        if point_count > 128 {
            return Err(BoardError(format!(
                "this reference implementation supports at most 128 points; {}x{} has {}",
                size, size, point_count
            )));
        }

        let full_mask = if point_count == 128 {
            Mask::MAX
        } else {
            (1u128 << point_count) - 1
        };
        let completion_len = point_count
            .checked_mul(point_count)
            .and_then(|x| x.checked_mul(point_count))
            .ok_or_else(|| BoardError("completion-table size overflow".into()))?;
        let mut completion = vec![0u128; completion_len];
        let mut forbidden_quadruples = 0u64;

        for a in 0..point_count {
            for b in (a + 1)..point_count {
                for c in (b + 1)..point_count {
                    for d in (c + 1)..point_count {
                        if is_forbidden_quad(size, a, b, c, d) {
                            forbidden_quadruples += 1;
                            let q = [a, b, c, d];
                            for omit in 0..4 {
                                let mut triple = [0usize; 3];
                                let mut out = 0usize;
                                for (i, &p) in q.iter().enumerate() {
                                    if i != omit {
                                        triple[out] = p;
                                        out += 1;
                                    }
                                }
                                let index = triple_index(point_count, triple[0], triple[1], triple[2]);
                                completion[index] |= bit(q[omit]);
                            }
                        }
                    }
                }
            }
        }

        let mut symmetry_maps = vec![vec![0usize; point_count]; 8];
        for p in 0..point_count {
            let (x, y) = (p % size, p / size);
            let n1 = size - 1;
            let transformed = [
                (x, y),
                (n1 - x, y),
                (x, n1 - y),
                (n1 - x, n1 - y),
                (y, x),
                (n1 - y, x),
                (y, n1 - x),
                (n1 - y, n1 - x),
            ];
            for (t, &(tx, ty)) in transformed.iter().enumerate() {
                symmetry_maps[t][p] = ty * size + tx;
            }
        }

        Ok(Self {
            size,
            point_count,
            full_mask,
            completion,
            symmetry_maps,
            forbidden_quadruples,
        })
    }

    pub fn size(&self) -> usize {
        self.size
    }

    pub fn point_count(&self) -> usize {
        self.point_count
    }

    pub fn full_mask(&self) -> Mask {
        self.full_mask
    }

    pub fn forbidden_quadruples(&self) -> u64 {
        self.forbidden_quadruples
    }

    pub fn point_id(&self, x: usize, y: usize) -> Result<usize, BoardError> {
        if x >= self.size || y >= self.size {
            return Err(BoardError(format!(
                "coordinate ({x},{y}) is outside a {}x{} board",
                self.size, self.size
            )));
        }
        Ok(y * self.size + x)
    }

    pub fn coordinates(&self, id: usize) -> Result<(usize, usize), BoardError> {
        if id >= self.point_count {
            return Err(BoardError(format!(
                "point id {id} is outside 0..{}",
                self.point_count
            )));
        }
        Ok((id % self.size, id / self.size))
    }

    pub fn mask_from_ids<I>(&self, ids: I) -> Result<Mask, BoardError>
    where
        I: IntoIterator<Item = usize>,
    {
        let mut mask = 0u128;
        for id in ids {
            if id >= self.point_count {
                return Err(BoardError(format!(
                    "point id {id} is outside 0..{}",
                    self.point_count
                )));
            }
            let b = bit(id);
            if mask & b != 0 {
                return Err(BoardError(format!("point id {id} appears twice")));
            }
            mask |= b;
        }
        Ok(mask)
    }

    /// Reconstructs the legal moves from scratch.
    ///
    /// A point is illegal if it is already occupied or if, together with any
    /// three occupied points, it makes a concyclic/collinear quadruple.
    pub fn legal_mask(&self, occupied: Mask) -> Result<Mask, BoardError> {
        if occupied & !self.full_mask != 0 {
            return Err(BoardError("state contains bits outside the board".into()));
        }
        let points = ids_from_mask(occupied);
        let mut banned = 0u128;
        for i in 0..points.len() {
            for j in (i + 1)..points.len() {
                for k in (j + 1)..points.len() {
                    let index = triple_index(
                        self.point_count,
                        points[i],
                        points[j],
                        points[k],
                    );
                    banned |= self.completion[index];
                }
            }
        }
        Ok(self.full_mask & !occupied & !banned)
    }

    pub fn is_valid_position(&self, occupied: Mask) -> Result<bool, BoardError> {
        if occupied & !self.full_mask != 0 {
            return Err(BoardError("state contains bits outside the board".into()));
        }
        let points = ids_from_mask(occupied);
        for i in 0..points.len() {
            for j in (i + 1)..points.len() {
                for k in (j + 1)..points.len() {
                    let index = triple_index(
                        self.point_count,
                        points[i],
                        points[j],
                        points[k],
                    );
                    if self.completion[index] & occupied != 0 {
                        return Ok(false);
                    }
                }
            }
        }
        Ok(true)
    }

    pub fn transform_point(&self, id: usize, transform: usize) -> Result<usize, BoardError> {
        if id >= self.point_count {
            return Err(BoardError(format!("point id {id} is outside the board")));
        }
        self.symmetry_maps
            .get(transform)
            .map(|map| map[id])
            .ok_or_else(|| BoardError(format!("symmetry transform must be 0..7, got {transform}")))
    }

    pub fn inverse_transform_point(
        &self,
        transformed_id: usize,
        transform: usize,
    ) -> Result<usize, BoardError> {
        if transformed_id >= self.point_count {
            return Err(BoardError(format!(
                "point id {transformed_id} is outside the board"
            )));
        }
        let map = self
            .symmetry_maps
            .get(transform)
            .ok_or_else(|| BoardError(format!("symmetry transform must be 0..7, got {transform}")))?;
        map.iter()
            .position(|&p| p == transformed_id)
            .ok_or_else(|| BoardError("symmetry map is not bijective".into()))
    }

    pub fn transform_mask(&self, mut mask: Mask, transform: usize) -> Result<Mask, BoardError> {
        let map = self
            .symmetry_maps
            .get(transform)
            .ok_or_else(|| BoardError(format!("symmetry transform must be 0..7, got {transform}")))?;
        let mut result = 0u128;
        while mask != 0 {
            let id = mask.trailing_zeros() as usize;
            mask &= mask - 1;
            result |= bit(map[id]);
        }
        Ok(result)
    }

    pub fn canonical(&self, occupied: Mask) -> Mask {
        let mut best = occupied;
        for transform in 1..8 {
            // Transform indices are guaranteed valid here.
            let candidate = self.transform_mask(occupied, transform).unwrap();
            if candidate < best {
                best = candidate;
            }
        }
        best
    }

    pub fn transpose_point(&self, id: usize) -> Result<usize, BoardError> {
        self.transform_point(id, 4)
    }
}

fn bit(id: usize) -> Mask {
    1u128 << id
}

fn ids_from_mask(mut mask: Mask) -> Vec<usize> {
    let mut ids = Vec::with_capacity(mask.count_ones() as usize);
    while mask != 0 {
        let id = mask.trailing_zeros() as usize;
        mask &= mask - 1;
        ids.push(id);
    }
    ids
}

fn triple_index(v: usize, a: usize, b: usize, c: usize) -> usize {
    debug_assert!(a < b && b < c);
    (a * v + b) * v + c
}

fn det3(rows: [[i128; 3]; 3]) -> i128 {
    let [[a, b, c], [d, e, f], [g, h, i]] = rows;
    a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
}

/// Uses a translated 3x3 determinant, rather than the optimized solver's
/// 4x4 determinant.  Collinear quadruples also produce determinant zero and
/// are forbidden by the game implementation being checked.
pub fn is_forbidden_quad(size: usize, a: usize, b: usize, c: usize, d: usize) -> bool {
    let (x0, y0) = ((a % size) as i128, (a / size) as i128);
    let others = [b, c, d];
    let mut rows = [[0i128; 3]; 3];
    for (r, &id) in others.iter().enumerate() {
        let x = (id % size) as i128;
        let y = (id / size) as i128;
        let dx = x - x0;
        let dy = y - y0;
        rows[r] = [dx, dy, dx * dx + dy * dy];
    }
    det3(rows) == 0
}
