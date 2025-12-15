import neomodel

ternary_choices = (
    ("valid", "valid"),
    ("invalid", "invalid"),
    ("unknown", "unknown"),
)
class Project(neomodel.StructuredNode):
    repo_url = neomodel.StringProperty(required=True)
    commit = neomodel.StringProperty(required=True)

    has_valid_dependencies = neomodel.StringProperty(choices=ternary_choices, default="unknown")
    has_valid_proof = neomodel.StringProperty(choices=ternary_choices, default="unknown")
    has_valid_paper = neomodel.StringProperty(choices=ternary_choices, default="unknown")

    dependencies = neomodel.RelationshipTo(
        "Project", "DEPENDS_ON"
    )
