from typing import List
import db

def get_all_user_ids_with_role(session, role_id) -> List[db.User]:
    """Returns a list of all users who currently have a role."""
    all_current_roles_list = session.query(db.GuildMemberRoles).filter_by(role_id=role_id).all()
    
    user_list = []

    for role in all_current_roles_list:
        user_list.append(role.member.user)

    return user_list