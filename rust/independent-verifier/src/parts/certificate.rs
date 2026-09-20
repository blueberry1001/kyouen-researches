#[derive(Clone, Copy, Debug)]
struct CertificateNode {
    state: Mask,
    outcome: u8,
    witness: u8,
    rank: u8,
}

#[derive(Clone, Debug)]
pub struct CertificateReport {
    pub board_size: usize,
    pub node_count: usize,
    pub losing_nodes: usize,
    pub winning_nodes: usize,
    pub forbidden_quadruples: u64,
    pub root_outcome: Outcome,
}

pub fn verify_certificate(path: &Path) -> Result<CertificateReport, String> {
    let bytes = fs::read(path)
        .map_err(|e| format!("cannot read certificate {}: {e}", path.display()))?;
    if bytes.len() < 40 {
        return Err("certificate is shorter than the 40-byte header".into());
    }
    if &bytes[0..7] != b"KYOENC3" {
        return Err("unsupported certificate magic".into());
    }

    let version = read_u32(&bytes, 8)?;
    if version != 3 {
        return Err(format!("unsupported certificate version {version}"));
    }
    let board_size = read_u32(&bytes, 12)? as usize;
    if !(1..=9).contains(&board_size) {
        return Err(format!("certificate board size {board_size} is outside 1..9"));
    }
    let node_count_u64 = read_u64(&bytes, 16)?;
    let node_count = usize::try_from(node_count_u64)
        .map_err(|_| "certificate node count does not fit usize".to_string())?;
    if node_count == 0 {
        return Err("certificate contains no nodes".into());
    }
    let root = read_u64(&bytes, 24)? as u128 | ((read_u32(&bytes, 32)? as u128) << 64);
    if root != 0 {
        return Err("classification certificate root is not the empty board".into());
    }
    let header_forbidden = read_u32(&bytes, 36)? as u64;

    let expected_size = 40usize
        .checked_add(
            node_count
                .checked_mul(16)
                .ok_or_else(|| "certificate size overflow".to_string())?,
        )
        .ok_or_else(|| "certificate size overflow".to_string())?;
    if bytes.len() != expected_size {
        return Err(format!(
            "certificate file size mismatch: expected {expected_size}, got {}",
            bytes.len()
        ));
    }

    let board = BoardSpec::new(board_size).map_err(|e| e.to_string())?;
    if board.forbidden_quadruples() != header_forbidden {
        return Err(format!(
            "forbidden quadruple count mismatch: header={header_forbidden}, recomputed={}",
            board.forbidden_quadruples()
        ));
    }

    let mut nodes = Vec::with_capacity(node_count);
    let mut table: HashMap<Mask, CertificateNode> = HashMap::with_capacity(node_count * 2);
    for index in 0..node_count {
        let offset = 40 + index * 16;
        let lo = read_u64(&bytes, offset)? as u128;
        let hi = read_u32(&bytes, offset + 8)? as u128;
        let node = CertificateNode {
            state: lo | (hi << 64),
            outcome: bytes[offset + 12],
            witness: bytes[offset + 13],
            rank: bytes[offset + 14],
        };
        let reserved = bytes[offset + 15];

        if node.outcome != 1 && node.outcome != 2 {
            return Err(format!("node {index} has invalid outcome {}", node.outcome));
        }
        if reserved != 0 {
            return Err(format!("node {index} has nonzero reserved byte"));
        }
        if node.state & !board.full_mask() != 0 {
            return Err(format!("node {index} uses bits outside the board"));
        }
        if node.rank as usize != board.point_count() - node.state.count_ones() as usize {
            return Err(format!("node {index} has an incorrect rank"));
        }
        if node.outcome == 1 && node.witness != 255 {
            return Err(format!("losing node {index} carries a witness"));
        }
        if board.canonical(node.state) != node.state {
            return Err(format!("node {index} is not in canonical form"));
        }
        if !board
            .is_valid_position(node.state)
            .map_err(|e| e.to_string())?
        {
            return Err(format!("node {index} contains a forbidden quadruple"));
        }
        if table.insert(node.state, node).is_some() {
            return Err(format!("node {index} duplicates an earlier state"));
        }
        nodes.push(node);
    }

    let root_node = table
        .get(&0)
        .copied()
        .ok_or_else(|| "root node is absent".to_string())?;
    if root_node.rank as usize != board.point_count() {
        return Err("root rank mismatch".into());
    }

    let mut losing_nodes = 0usize;
    let mut winning_nodes = 0usize;
    for (index, node) in nodes.iter().copied().enumerate() {
        let legal = board.legal_mask(node.state).map_err(|e| e.to_string())?;
        match node.outcome {
            2 => {
                winning_nodes += 1;
                let witness = node.witness as usize;
                if witness >= board.point_count() {
                    return Err(format!("winning node {index} has an invalid witness"));
                }
                let witness_bit = 1u128 << witness;
                if legal & witness_bit == 0 {
                    return Err(format!("winning node {index} witness is not legal"));
                }
                let child = board.canonical(node.state | witness_bit);
                let child_node = table.get(&child).ok_or_else(|| {
                    format!("winning node {index} witness child is absent from the certificate")
                })?;
                if child_node.outcome != 1 || child_node.rank >= node.rank {
                    return Err(format!(
                        "winning node {index} witness does not reach a smaller-rank losing node"
                    ));
                }
            }
            1 => {
                losing_nodes += 1;
                let mut unique = HashSet::new();
                for move_id in ids_from_mask(legal) {
                    let child = board.canonical(node.state | (1u128 << move_id));
                    if !unique.insert(child) {
                        continue;
                    }
                    let child_node = table.get(&child).ok_or_else(|| {
                        format!(
                            "losing node {index} has a legal child absent from the certificate"
                        )
                    })?;
                    if child_node.outcome != 2 || child_node.rank >= node.rank {
                        return Err(format!(
                            "losing node {index} has a child not certified winning at smaller rank"
                        ));
                    }
                }
            }
            _ => unreachable!(),
        }
    }

    let root_outcome = if root_node.outcome == 2 {
        Outcome::Winning
    } else {
        Outcome::Losing
    };
    Ok(CertificateReport {
        board_size,
        node_count,
        losing_nodes,
        winning_nodes,
        forbidden_quadruples: board.forbidden_quadruples(),
        root_outcome,
    })
}

fn read_u32(bytes: &[u8], offset: usize) -> Result<u32, String> {
    let end = offset
        .checked_add(4)
        .ok_or_else(|| "certificate offset overflow".to_string())?;
    let slice = bytes
        .get(offset..end)
        .ok_or_else(|| "unexpected end of certificate".to_string())?;
    Ok(u32::from_le_bytes(slice.try_into().unwrap()))
}

fn read_u64(bytes: &[u8], offset: usize) -> Result<u64, String> {
    let end = offset
        .checked_add(8)
        .ok_or_else(|| "certificate offset overflow".to_string())?;
    let slice = bytes
        .get(offset..end)
        .ok_or_else(|| "unexpected end of certificate".to_string())?;
    Ok(u64::from_le_bytes(slice.try_into().unwrap()))
}

#[cfg(test)]
mod certificate_tests {
    use super::*;

    fn one_by_one_certificate(witness: u8) -> Vec<u8> {
        let mut bytes = vec![0u8; 40 + 2 * 16];
        bytes[0..7].copy_from_slice(b"KYOENC3");
        bytes[8..12].copy_from_slice(&3u32.to_le_bytes());
        bytes[12..16].copy_from_slice(&1u32.to_le_bytes());
        bytes[16..24].copy_from_slice(&2u64.to_le_bytes());
        bytes[36..40].copy_from_slice(&0u32.to_le_bytes());

        let root = 40;
        bytes[root + 12] = 2;
        bytes[root + 13] = witness;
        bytes[root + 14] = 1;

        let child = 56;
        bytes[child..child + 8].copy_from_slice(&1u64.to_le_bytes());
        bytes[child + 12] = 1;
        bytes[child + 13] = 255;
        bytes[child + 14] = 0;
        bytes
    }

    #[test]
    fn verifies_minimal_one_by_one_certificate() {
        let path = std::env::temp_dir().join(format!(
            "kyouen-rust-cert-test-{}-ok.cert",
            std::process::id()
        ));
        fs::write(&path, one_by_one_certificate(0)).unwrap();
        let report = verify_certificate(&path).unwrap();
        fs::remove_file(path).ok();
        assert_eq!(report.board_size, 1);
        assert_eq!(report.node_count, 2);
        assert_eq!(report.root_outcome, Outcome::Winning);
    }

    #[test]
    fn rejects_illegal_winning_witness() {
        let path = std::env::temp_dir().join(format!(
            "kyouen-rust-cert-test-{}-bad.cert",
            std::process::id()
        ));
        fs::write(&path, one_by_one_certificate(1)).unwrap();
        let error = verify_certificate(&path).unwrap_err();
        fs::remove_file(path).ok();
        assert!(error.contains("invalid witness"));
    }
}
