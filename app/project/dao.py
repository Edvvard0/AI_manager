from app.dao.base import BaseDAO
from app.project.models import Project


class ProjectDAO(BaseDAO):
    model = Project