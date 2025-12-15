-- Topology fundamentals
namespace TopologyBasics

-- Open set definition
def isOpen {X : Type} (topology : Set (Set X)) (U : Set X) : Prop :=
  U ∈ topology

-- Closed set definition
def isClosed {X : Type} (topology : Set (Set X)) (C : Set X) : Prop :=
  isOpen topology (Cᶜ)

end TopologyBasics
