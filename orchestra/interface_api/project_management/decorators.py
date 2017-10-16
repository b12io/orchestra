from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from jsonview.decorators import json_view


def is_project_admin(user):
    return (user.groups.filter(name='project_admins').exists() or
            user.is_superuser)


def is_project_member_or_admin(user, project):
    return (project.tasks.filter(assignments__worker__user=user).count() > 0 or
            is_project_admin(user))


def project_management_api_view_base(func):
    @json_view
    @login_required
    def func_wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return func_wrapper


def project_management_api_view(func):
    @project_management_api_view_base
    @user_passes_test(is_project_admin)
    def func_wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return func_wrapper
