import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from security.permissions import User, can_user_access, filter_authorized_chunks


HR_POLICY = {"source": "hr_policy.pdf", "allowed_roles": ["HR", "employee", "admin"], "min_role_level": 10}
FINANCE = {"source": "balance_sheet.pdf", "allowed_roles": ["finance", "admin"], "min_role_level": 50}
ENGINEERING = {"source": "engineering_sop.pdf", "allowed_roles": ["engineer", "admin"], "min_role_level": 50}
CONFIDENTIAL_ADMIN = {"source": "board_minutes.pdf", "allowed_roles": ["admin"], "min_role_level": 100}
EMPLOYEE_DOC = {"source": "employee_handbook.pdf", "allowed_roles": ["employee"], "min_role_level": 10}


def test_role_matrix_matches_required_access():
    assert can_user_access(User("alice", "HR"), HR_POLICY)
    assert not can_user_access(User("alice", "HR"), FINANCE)
    assert can_user_access(User("bob", "Employee"), HR_POLICY)
    assert not can_user_access(User("bob", "Employee"), FINANCE)
    assert can_user_access(User("charlie", "Finance"), FINANCE)
    assert can_user_access(User("dave", "Engineer"), ENGINEERING)
    assert can_user_access(User("root", "Superuser"), CONFIDENTIAL_ADMIN)


def test_hierarchy_admin_eng_emp():
    # Admin accesses all documents
    admin = User("admin_user", "admin")
    assert can_user_access(admin, CONFIDENTIAL_ADMIN)
    assert can_user_access(admin, ENGINEERING)
    assert can_user_access(admin, EMPLOYEE_DOC)

    # Engineer accesses engineer and employee docs, but NOT admin-only
    eng = User("eng_user", "eng")
    assert can_user_access(eng, ENGINEERING)
    assert can_user_access(eng, EMPLOYEE_DOC)
    assert not can_user_access(eng, CONFIDENTIAL_ADMIN)

    # Employee accesses employee docs, but NOT engineer or admin-only
    emp = User("emp_user", "emp")
    assert can_user_access(emp, EMPLOYEE_DOC)
    assert not can_user_access(emp, ENGINEERING)
    assert not can_user_access(emp, CONFIDENTIAL_ADMIN)


def test_uploader_always_has_access():
    # A low-privilege employee who uploaded a document can access it
    doc = {"source": "my_notes.txt", "allowed_roles": ["engineer"], "uploaded_by": "john_doe"}
    john = User("john_doe", "employee")
    assert can_user_access(john, doc)

    # Another employee cannot access it
    other = User("other_emp", "employee")
    assert not can_user_access(other, doc)


def test_filter_removes_unauthorized_chunks_before_results():
    user = User("bob", "employee")
    visible = filter_authorized_chunks(user, [HR_POLICY, FINANCE, CONFIDENTIAL_ADMIN])
    assert [chunk["source"] for chunk in visible] == ["hr_policy.pdf"]


def test_missing_identity_or_roles_denies_access():
    assert not can_user_access(User("", "admin"), HR_POLICY)
    assert not can_user_access(User("bob", "employee"), {"source": "unclassified.txt"})