"""Webhook event subscriptions must use exact JSON array membership."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import WebhookRepository


async def test_exact_webhook_event_membership(db_session: AsyncSession) -> None:
    repository = WebhookRepository(db_session)
    exact = await repository.create(
        "exact", "https://example.com/hook", ["download.completed"]
    )
    multiple = await repository.create(
        "multiple",
        "https://example.com/hook",
        ["download.failed", "download.completed"],
    )
    await repository.create(
        "prefix", "https://example.com/hook", ["download.completed.extra"]
    )
    await repository.create("short", "https://example.com/hook", ["download"])
    inactive = await repository.create(
        "inactive", "https://example.com/hook", ["download.completed"]
    )
    inactive.is_active = False
    await db_session.commit()

    matches = await repository.get_webhooks_for_event("download.completed")
    assert {hook.id for hook in matches} == {exact.id, multiple.id}
    assert await repository.get_webhooks_for_event("download.missing") == []
