import Std

namespace Kyouen

/-- The label stored in a game certificate. -/
inductive Outcome where
  | losing
  | winning
deriving Repr, BEq, DecidableEq

mutual
  /-- A state is winning when it has a legal move to a losing state. -/
  inductive Winning {σ : Type u} (moves : σ → List σ) : σ → Prop where
    | move {s t : σ} : t ∈ moves s → Losing moves t → Winning moves s

  /-- A state is losing when every legal move leads to a winning state. -/
  inductive Losing {σ : Type u} (moves : σ → List σ) : σ → Prop where
    | all {s : σ} : (∀ t, t ∈ moves s → Winning moves t) → Losing moves s
end

/-- A certificate entry. `rank` only has to decrease along checked edges. -/
structure Entry where
  outcome : Outcome
  rank : Nat
deriving Repr, BEq, DecidableEq

/-- A partial certificate: states outside the proof DAG may be absent. -/
abbrev Certificate (σ : Type u) := σ → Option Entry

/--
Local conditions sufficient for a sound AND/OR proof.

* A winning node supplies one legal losing child of smaller rank.
* A losing node supplies every legal child, each winning and of smaller rank.
-/
def LocallyValid {σ : Type u}
    (moves : σ → List σ) (cert : Certificate σ) : Prop :=
  ∀ s e, cert s = some e →
    match e.outcome with
    | .winning =>
        ∃ t child,
          t ∈ moves s ∧
          cert t = some child ∧
          child.outcome = .losing ∧
          child.rank < e.rank
    | .losing =>
        ∀ t, t ∈ moves s →
          ∃ child,
            cert t = some child ∧
            child.outcome = .winning ∧
            child.rank < e.rank

mutual
/-- A locally valid winning entry denotes a genuinely winning game state. -/
theorem winning_sound {σ : Type u}
    {moves : σ → List σ} {cert : Certificate σ}
    (hvalid : LocallyValid moves cert)
    {s : σ} {e : Entry}
    (hs : cert s = some e)
    (hout : e.outcome = .winning) :
    Winning moves s := by
  have hlocal := hvalid s e hs
  rw [hout] at hlocal
  rcases hlocal with ⟨t, child, hmem, hchild, hchildOutcome, hlt⟩
  exact Winning.move hmem (losing_sound hvalid hchild hchildOutcome)
termination_by e.rank
decreasing_by exact hlt

/-- A locally valid losing entry denotes a genuinely losing game state. -/
theorem losing_sound {σ : Type u}
    {moves : σ → List σ} {cert : Certificate σ}
    (hvalid : LocallyValid moves cert)
    {s : σ} {e : Entry}
    (hs : cert s = some e)
    (hout : e.outcome = .losing) :
    Losing moves s := by
  apply Losing.all
  intro t hmem
  have hlocal := hvalid s e hs
  rw [hout] at hlocal
  rcases hlocal t hmem with ⟨child, hchild, hchildOutcome, hlt⟩
  exact winning_sound hvalid hchild hchildOutcome
termination_by e.rank
decreasing_by exact hlt
end

/-- Convenient root theorem for a certificate whose root is labelled winning. -/
theorem root_winning_of_valid {σ : Type u}
    {moves : σ → List σ} {cert : Certificate σ}
    (hvalid : LocallyValid moves cert)
    {root : σ} {rank : Nat}
    (hroot : cert root = some { outcome := .winning, rank := rank }) :
    Winning moves root :=
  winning_sound hvalid hroot rfl

/-- Convenient root theorem for a certificate whose root is labelled losing. -/
theorem root_losing_of_valid {σ : Type u}
    {moves : σ → List σ} {cert : Certificate σ}
    (hvalid : LocallyValid moves cert)
    {root : σ} {rank : Nat}
    (hroot : cert root = some { outcome := .losing, rank := rank }) :
    Losing moves root :=
  losing_sound hvalid hroot rfl

/-- A first move is winning when it leaves a losing state to the opponent. -/
def WinningFirstMove {σ : Type u} (moves : σ → List σ) (empty after : σ) : Prop :=
  after ∈ moves empty ∧ Losing moves after

end Kyouen
