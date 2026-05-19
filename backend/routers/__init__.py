from .dynamics import router as dynamics_router
from .favorites import router as favorites_router
from .followings import router as followings_router
from .history import router as history_router
from .me import router as me_router
from .tag import router as tag_router
from .tasks import router as tasks_router
from .users import router as users_router

__all__ = [
    "dynamics_router",
    "favorites_router",
    "followings_router",
    "history_router",
    "me_router",
    "tag_router",
    "tasks_router",
    "users_router",
]
