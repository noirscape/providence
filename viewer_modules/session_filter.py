from typing import List
import db

def get_all_user_ids_with_role(session, role_id) -> List[db.User]:
    """Returns a list of all users who currently have a role."""
    all_audits_for_role = session.query(db.RoleAudit).filter_by(role_id=role_id).all()
    
    user_list = []

    for audit in all_audits_for_role:
        if audit.role_was_added:
            user_list.append(audit.member.user_id)
        else:
            if audit.member.user_id in user_list:
                user_list.remove(audit.member.user_id)

    return user_list