import neomodel

ternary_choices = (
    ("valid", "valid"),
    ("invalid", "invalid"),
    ("unknown", "unknown"),
)
class Project(neomodel.StructuredNode):
    # Note: indexes are required for neomodel to add this node type to the schema
    repo_url = neomodel.StringProperty(required=True, index=True)
    commit = neomodel.StringProperty(required=True, index=True)

    has_valid_dependencies = neomodel.StringProperty(choices=ternary_choices, default="unknown")
    has_valid_proof = neomodel.StringProperty(choices=ternary_choices, default="unknown")
    has_valid_paper = neomodel.StringProperty(choices=ternary_choices, default="unknown")

    dependencies = neomodel.RelationshipTo(
        "Project", "DEPENDS_ON"
    )
