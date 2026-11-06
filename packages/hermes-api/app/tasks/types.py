"""Preserve task signatures across Celery's untyped decorator boundary."""

from collections.abc import Callable
from typing import ParamSpec, Protocol, TypeVar, cast

from app.tasks.celery_app import celery_app

P = ParamSpec("P")
R = TypeVar("R", covariant=True)


class Task(Protocol[P, R]):
    @property
    def name(self) -> str: ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...

    def apply_async(
        self,
        args: tuple[object, ...] = (),
        kwargs: dict[str, object] | None = None,
        *,
        task_id: str | None = None,
        queue: str | None = None,
    ) -> object: ...


def task(
    *, name: str, acks_late: bool = False, reject_on_worker_lost: bool = False
) -> Callable[[Callable[P, R]], Task[P, R]]:
    def decorate(function: Callable[P, R]) -> Task[P, R]:
        return cast(
            Task[P, R],
            celery_app.task(
                name=name,
                acks_late=acks_late,
                reject_on_worker_lost=reject_on_worker_lost,
            )(function),
        )

    return decorate
