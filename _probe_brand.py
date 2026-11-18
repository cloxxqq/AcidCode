import asyncio

from acidcode.app import AcidCode


async def main() -> None:
    app = AcidCode()
    async with app.run_test(size=(120, 34)) as pilot:
        await pilot.pause(0.2)
        screen = app.screen
        print("screen:", type(screen).__name__)
        text = screen.query_one("#splash-text")
        print("splash:", repr(str(text.render()).splitlines()[:3]))
        app.exit()


asyncio.run(main())
