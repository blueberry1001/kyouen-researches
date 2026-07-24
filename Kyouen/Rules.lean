import Std
import Kyouen.CertificateSoundness

namespace Kyouen.SquareBoard

/-- A point of an `n × n` lattice-point board, stored in row-major order. -/
abbrev Point (n : Nat) := Fin (n * n)
abbrev Position (n : Nat) := Finset (Point n)

private def x {n : Nat} (p : Point n) : Int := Int.ofNat (p.val % n)
private def y {n : Nat} (p : Point n) : Int := Int.ofNat (p.val / n)
private def q {n : Nat} (p : Point n) : Int := x p * x p + y p * y p

private def det3
    (a₀ a₁ a₂ b₀ b₁ b₂ c₀ c₁ c₂ : Int) : Int :=
  a₀ * (b₁ * c₂ - b₂ * c₁) -
  a₁ * (b₀ * c₂ - b₂ * c₀) +
  a₂ * (b₀ * c₁ - b₁ * c₀)

/-- The 4×4 determinant for concyclicity, including the collinear case. -/
def determinant4 {n : Nat} (a b c d : Point n) : Int :=
  q a * det3 (x b) (y b) 1 (x c) (y c) 1 (x d) (y d) 1 -
  x a * det3 (q b) (y b) 1 (q c) (y c) 1 (q d) (y d) 1 +
  y a * det3 (q b) (x b) 1 (q c) (x c) 1 (q d) (x d) 1 -
        det3 (q b) (x b) (y b) (q c) (x c) (y c) (q d) (x d) (y d)

/-- Four distinct points are forbidden when they are concyclic or collinear. -/
def ForbiddenFour {n : Nat} (a b c d : Point n) : Prop :=
  a ≠ b ∧ a ≠ c ∧ a ≠ d ∧
  b ≠ c ∧ b ≠ d ∧ c ≠ d ∧
  determinant4 a b c d = 0

instance {n : Nat} (a b c d : Point n) : Decidable (ForbiddenFour a b c d) := inferInstance

/-- A position already contains a forbidden quadruple. -/
def ContainsForbidden {n : Nat} (s : Position n) : Prop :=
  ∃ a ∈ s, ∃ b ∈ s, ∃ c ∈ s, ∃ d ∈ s, ForbiddenFour a b c d

instance {n : Nat} (s : Position n) : Decidable (ContainsForbidden s) := inferInstance

/-- A safe move adds an unused point without creating a forbidden quadruple. -/
def LegalMove {n : Nat} (s : Position n) (p : Point n) : Prop :=
  p ∉ s ∧ ¬ ContainsForbidden (insert p s)

instance {n : Nat} (s : Position n) (p : Point n) : Decidable (LegalMove s p) := inferInstance

/-- All safe child positions. -/
def moves (n : Nat) (s : Position n) : List (Position n) :=
  (List.finRange (n * n)).filterMap fun p =>
    if LegalMove s p then some (insert p s) else none

/-- The empty position on an `n × n` board. -/
def empty (n : Nat) : Position n := ∅

end Kyouen.SquareBoard

namespace Kyouen.NineByNine

abbrev Point := SquareBoard.Point 9
abbrev Position := SquareBoard.Position 9

def moves : Position → List Position := SquareBoard.moves 9
def empty : Position := SquareBoard.empty 9

def center : Point := ⟨40, by decide⟩
def afterCenter : Position := {center}

end Kyouen.NineByNine
