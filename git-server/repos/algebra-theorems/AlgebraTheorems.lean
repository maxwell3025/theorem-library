-- Algebraic theorems building on BaseMath
import BaseMath

namespace AlgebraTheorems

-- Theorem about even numbers
theorem sum_of_evens_is_even (a b : Nat)
  (ha : BaseMath.isEven a = true)
  (hb : BaseMath.isEven b = true) :
  BaseMath.isEven (a + b) = true := by
  sorry

end AlgebraTheorems
