use std::fs::File;
use std::io::{Read, Seek, SeekFrom};

#[derive(Clone, Copy, Debug)]
struct CertificateNode {
    state: Mask,
    outcome: u8,
    witness: u8,
    rank: u8,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum CertificateFormat {
    V3,
    V4,
}

impl CertificateFormat {
    fn version(self) -> u32 {
        match self {
            Self::V3 => 3,
            Self::V4 => 4,
        }
    }

    fn header_size(self) -> usize {
        match self {
            Self::V3 => 40,
            Self::V4 => 48,
        }
    }

    fn node_size(self) -> usize {
        match self {
            Self::V3 => 16,
            Self::V4 => 24,
        }
    }
}

#[derive(Clone, Debug)]
pub struct CertificateReport {
    pub format_version: u32,
    pub board_size: usize,
    pub node_count: usize,
    pub losing_nodes: usize,
    pub winning_nodes: usize,
    pub forbidden_quadruples: u64,
    pub root_state: Mask,
    pub root_outcome: Outcome,
}

pub fn verify_certificate(path: &Path) -> Result<CertificateReport, String> {
    let mut file = File::open(path)
        .map_err(|e| format!("cannot open certificate {}: {e}", path.display()))?;
    let file_size = file
        .metadata()
        .map_err(|e| format!("cannot stat certificate {}: {e}", path.display()))?
        .len();

    let mut magic = [0u8; 8];
    file.read_exact(&mut magic)
        .map_err(|_| "certificate is shorter than the magic field".to_string())?;
    let format = if &magic[0..7] == b"KYOENC3" {
        CertificateFormat::V3
    } else if &magic[0..7] == b"KYOENC4" {
        CertificateFormat::V4
    } else {
        return Err("unsupported certificate magic".into());
    };

    file.seek(SeekFrom::Start(0))
        .map_err(|e| format!("cannot seek certificate: {e}"))?;
    let mut header = vec![0u8; format.header_size()];
    file.read_exact(&mut header)
        .map_err(|_| format!("certificate is shorter than the {}-byte header", format.header_size()))?;

    let version = read_u32(&header, 8)?;
    if version != format.version() {
        return Err(format!(
            "certificate magic/version mismatch: magic implies {}, header says {version}",
            format.version()
        ));
    }
    let board_size = read_u32(&header, 12)? as usize;
    let point_count = board_size
        .checked_mul(board_size)
        .ok_or_else(|| "certificate board size overflow".to_string())?;
    if board_size == 0 || point_count > 128 {
        return Err(format!(
            "certificate board size {board_size} is unsupported; at most 128 points are allowed"
        ));
    }
    if format == CertificateFormat::V3 && board_size > 9 {
        return Err(format!(
            "KYOENC3 board size {board_size} is outside its 1..9 range"
        ));
    }

    let node_count_u64 = read_u64(&header, 16)?;
    let node_count = usize::try_from(node_count_u64)
        .map_err(|_| "certificate node count does not fit usize".to_string())?;
    if node_count == 0 {
        return Err("certificate contains no nodes".into());
    }

    let (root, header_forbidden) = match format {
        CertificateFormat::V3 => {
            let root = read_u64(&header, 24)? as u128
                | ((read_u32(&header, 32)? as u128) << 64);
            if root != 0 {
                return Err("KYOENC3 classification certificate root is not the empty board".into());
            }
            (root, read_u32(&header, 36)? as u64)
        }
        CertificateFormat::V4 => {
            let root = read_u64(&header, 24)? as u128
                | ((read_u64(&header, 32)? as u128) << 64);
            (root, read_u64(&header, 40)?)
        }
    };

    let expected_size = (format.header_size() as u64)
        .checked_add(
            node_count_u64
                .checked_mul(format.node_size() as u64)
                .ok_or_else(|| "certificate size overflow".to_string())?,
        )
        .ok_or_else(|| "certificate size overflow".to_string())?;
    if file_size != expected_size {
        return Err(format!(
            "certificate file size mismatch: expected {expected_size}, got {file_size}"
        ));
    }

    let board = BoardSpec::new(board_size).map_err(|e| e.to_string())?;
    if root & !board.full_mask() != 0 {
        return Err("certificate root uses bits outside the board".into());
    }
    if board.canonical(root) != root {
        return Err("certificate root is not in canonical form".into());
    }
    if !board.is_valid_position(root).map_err(|e| e.to_string())? {
        return Err("certificate root contains a forbidden quadruple".into());
    }
    if board.forbidden_quadruples() != header_forbidden {
        return Err(format!(
            "forbidden quadruple count mismatch: header={header_forbidden}, recomputed={}",
            board.forbidden_quadruples()
        ));
    }

    // First streaming pass: validate and index compact node records. The raw
    // certificate bytes are not retained in memory.
    let capacity = node_count
        .checked_mul(2)
        .unwrap_or(node_count);
    let mut table: HashMap<Mask, CertificateNode> = HashMap::with_capacity(capacity);
    file.seek(SeekFrom::Start(format.header_size() as u64))
        .map_err(|e| format!("cannot seek to certificate nodes: {e}"))?;
    let mut node_bytes = vec![0u8; format.node_size()];
    for index in 0..node_count {
        file.read_exact(&mut node_bytes)
            .map_err(|_| format!("unexpected end while reading node {index}"))?;
        let node = parse_node(format, &node_bytes, index)?;
        validate_node(&board, node, index)?;
        if table.insert(node.state, node).is_some() {
            return Err(format!("node {index} duplicates an earlier state"));
        }
    }

    let root_node = table
        .get(&root)
        .copied()
        .ok_or_else(|| "root node is absent".to_string())?;
    let expected_root_rank = board.point_count() - root.count_ones() as usize;
    if root_node.rank as usize != expected_root_rank {
        return Err("root rank mismatch".into());
    }

    // Second streaming pass: verify local proof obligations. A WIN node needs
    // one certified LOSS child. A LOSS node needs every distinct legal child
    // certified WIN. Rank decreases by exactly one on each edge.
    file.seek(SeekFrom::Start(format.header_size() as u64))
        .map_err(|e| format!("cannot rewind certificate nodes: {e}"))?;
    let mut losing_nodes = 0usize;
    let mut winning_nodes = 0usize;
    for index in 0..node_count {
        file.read_exact(&mut node_bytes)
            .map_err(|_| format!("unexpected end during proof pass at node {index}"))?;
        let node = parse_node(format, &node_bytes, index)?;
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
                if child_node.outcome != 1 || child_node.rank.checked_add(1) != Some(node.rank) {
                    return Err(format!(
                        "winning node {index} witness does not reach a rank-minus-one losing node"
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
                    if child_node.outcome != 2
                        || child_node.rank.checked_add(1) != Some(node.rank)
                    {
                        return Err(format!(
                            "losing node {index} has a child not certified winning at rank minus one"
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
        format_version: version,
        board_size,
        node_count,
        losing_nodes,
        winning_nodes,
        forbidden_quadruples: board.forbidden_quadruples(),
        root_state: root,
        root_outcome,
    })
}

fn parse_node(
    format: CertificateFormat,
    bytes: &[u8],
    index: usize,
) -> Result<CertificateNode, String> {
    let lo = read_u64(bytes, 0)? as u128;
    match format {
        CertificateFormat::V3 => {
            let hi = read_u32(bytes, 8)? as u128;
            if bytes[15] != 0 {
                return Err(format!("node {index} has nonzero reserved byte"));
            }
            Ok(CertificateNode {
                state: lo | (hi << 64),
                outcome: bytes[12],
                witness: bytes[13],
                rank: bytes[14],
            })
        }
        CertificateFormat::V4 => {
            let hi = read_u64(bytes, 8)? as u128;
            if bytes[19] != 0 || read_u32(bytes, 20)? != 0 {
                return Err(format!("node {index} has nonzero flags or reserved field"));
            }
            Ok(CertificateNode {
                state: lo | (hi << 64),
                outcome: bytes[16],
                witness: bytes[17],
                rank: bytes[18],
            })
        }
    }
}

fn validate_node(
    board: &BoardSpec,
    node: CertificateNode,
    index: usize,
) -> Result<(), String> {
    if node.outcome != 1 && node.outcome != 2 {
        return Err(format!("node {index} has invalid outcome {}", node.outcome));
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
    Ok(())
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

    fn one_by_one_v3(witness: u8) -> Vec<u8> {
        let mut bytes = vec![0u8; 40 + 2 * 16];
        bytes[0..7].copy_from_slice(b"KYOENC3");
        bytes[8..12].copy_from_slice(&3u32.to_le_bytes());
        bytes[12..16].copy_from_slice(&1u32.to_le_bytes());
        bytes[16..24].copy_from_slice(&2u64.to_le_bytes());

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

    fn one_by_one_v4_nonempty_root() -> Vec<u8> {
        let mut bytes = vec![0u8; 48 + 24];
        bytes[0..7].copy_from_slice(b"KYOENC4");
        bytes[8..12].copy_from_slice(&4u32.to_le_bytes());
        bytes[12..16].copy_from_slice(&1u32.to_le_bytes());
        bytes[16..24].copy_from_slice(&1u64.to_le_bytes());
        bytes[24..32].copy_from_slice(&1u64.to_le_bytes());

        let node = 48;
        bytes[node..node + 8].copy_from_slice(&1u64.to_le_bytes());
        bytes[node + 16] = 1;
        bytes[node + 17] = 255;
        bytes[node + 18] = 0;
        bytes
    }

    fn temp_path(name: &str) -> PathBuf {
        std::env::temp_dir().join(format!(
            "kyouen-rust-cert-test-{}-{name}.cert",
            std::process::id()
        ))
    }

    #[test]
    fn verifies_minimal_one_by_one_v3_certificate() {
        let path = temp_path("v3-ok");
        fs::write(&path, one_by_one_v3(0)).unwrap();
        let report = verify_certificate(&path).unwrap();
        fs::remove_file(path).ok();
        assert_eq!(report.format_version, 3);
        assert_eq!(report.board_size, 1);
        assert_eq!(report.node_count, 2);
        assert_eq!(report.root_state, 0);
        assert_eq!(report.root_outcome, Outcome::Winning);
    }

    #[test]
    fn verifies_nonempty_kyoenc4_root() {
        let path = temp_path("v4-root");
        fs::write(&path, one_by_one_v4_nonempty_root()).unwrap();
        let report = verify_certificate(&path).unwrap();
        fs::remove_file(path).ok();
        assert_eq!(report.format_version, 4);
        assert_eq!(report.root_state, 1);
        assert_eq!(report.root_outcome, Outcome::Losing);
    }

    #[test]
    fn rejects_illegal_winning_witness() {
        let path = temp_path("bad-witness");
        fs::write(&path, one_by_one_v3(1)).unwrap();
        let error = verify_certificate(&path).unwrap_err();
        fs::remove_file(path).ok();
        assert!(error.contains("invalid witness"));
    }
}
