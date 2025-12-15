-- Calculus fundamentals
namespace CalcBasics

-- Limit definition
def hasLimit (f : ℝ → ℝ) (x : ℝ) (L : ℝ) : Prop :=
  ∀ ε > 0, ∃ δ > 0, ∀ x', |x' - x| < δ → |f x' - L| < ε

end CalcBasics
