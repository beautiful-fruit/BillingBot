from dotenv import load_dotenv

from asyncio import get_event_loop, run


async def main():
    loop = get_event_loop()

    from bot import start
    import slash_commands
    from db import init_db, get_db
    from repository.summary_repository import SummaryRepository
    from timeout_manager import task as timeout_task

    loop.create_task(timeout_task())

    async with init_db():
        await start()


if __name__ == "__main__":
    load_dotenv()
    try:
        run(main=main())
    except KeyboardInterrupt:
        pass
