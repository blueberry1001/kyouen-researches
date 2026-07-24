import Kyouen.CertificateSoundness
import Kyouen.Rules

open Kyouen

/-
A tiny finite game used as a compile-time demonstration of
certificate soundness.
-/
namespace Demo

inductive State where
  | root
  | leaf
deriving Repr, BEq, DecidableEq

open State

def moves : State → List State
  | root => [leaf]
  | leaf => []

def cert : Certificate State
  | root =>
      some {
        outcome := .winning
        rank := 1
      }
  | leaf =>
      some {
        outcome := .losing
        rank := 0
      }

theorem cert_valid : LocallyValid moves cert := by
  intro s e hs
  cases s with
  | root =>
      simp only [cert, Option.some.injEq] at hs
      subst e
      exact ⟨
        leaf,
        { outcome := .losing, rank := 0 },
        by simp [moves],
        rfl,
        rfl,
        by decide
      ⟩
  | leaf =>
      simp only [cert, Option.some.injEq] at hs
      subst e
      intro t ht
      simp [moves] at ht

theorem root_is_winning : Winning moves root :=
  root_winning_of_valid cert_valid rfl

end Demo

def main : IO Unit := do
  IO.println
    "Kyouen 1–9: ranked AND/OR certificate soundness layer loaded."