from django.urls import path

from .views import (
    DistrictsView,
    RegionsView,
    RequestRepliesView,
    RoleNamesView,
    RolesFullView,
    RolesView,
    SpheresView,
    StatusesView,
    TaskRepliesView,
    TypesView,
)

urlpatterns = [
    path('spheres/', SpheresView.as_view(), name='info-spheres'),
    path('types/', TypesView.as_view(), name='info-types'),
    path('task-replies/', TaskRepliesView.as_view(), name='info-task-replies'),
    path('request-replies/', RequestRepliesView.as_view(), name='info-request-replies'),
    path('roles/', RolesView.as_view(), name='info-roles'),
    path('roles-full/', RolesFullView.as_view(), name='info-roles-full'),
    path('role-names/', RoleNamesView.as_view(), name='info-role-names'),
    path('statuses/', StatusesView.as_view(), name='info-statuses'),
    path('regions/', RegionsView.as_view(), name='info-regions'),
    path('districts/', DistrictsView.as_view(), name='info-districts'),
]
