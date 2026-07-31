#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn translated_determinant_detects_square_and_line() {
        assert!(is_forbidden_quad(4, 0, 1, 4, 5));
        assert!(is_forbidden_quad(4, 0, 1, 2, 3));
        assert!(!is_forbidden_quad(4, 0, 1, 4, 10));
    }

    #[test]
    fn legal_reconstruction_bans_fourth_square_corner() {
        let board = BoardSpec::new(4).unwrap();
        let state = board.mask_from_ids([0, 1, 4]).unwrap();
        assert_eq!(board.legal_mask(state).unwrap() & bit(5), 0);
    }

    #[test]
    fn symmetries_are_bijections_and_preserve_canonical_form() {
        let board = BoardSpec::new(5).unwrap();
        let state = board.mask_from_ids([0, 7, 13]).unwrap();
        let canonical = board.canonical(state);
        for t in 0..8 {
            let transformed = board.transform_mask(state, t).unwrap();
            assert_eq!(board.canonical(transformed), canonical);
            let mut image = HashSet::new();
            for p in 0..board.point_count() {
                image.insert(board.transform_point(p, t).unwrap());
            }
            assert_eq!(image.len(), board.point_count());
        }
    }

    #[test]
    fn known_small_board_results() {
        run_reference_self_test().unwrap();
    }
}
