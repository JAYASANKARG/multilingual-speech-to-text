"""Insert N sample entries: uv run python -m app.scripts.seed 50"""

import asyncio
import sys

from sqlalchemy import text

from app.core.db import engine

SAMPLES = [
    "Kal meeting hai at 10 AM, please send the report",
    "कल की meeting के बाद lunch करते हैं",
    "Let's review the quarterly numbers on Monday",
    "मुझे अपना password reset करना है",
    "Please call me back when you are free",
]


async def seed(n: int) -> None:
    async with engine.begin() as conn:
        for i in range(n):
            await conn.execute(
                text(
                    "INSERT INTO transcriptions (text, source, languages, engine, created_at) "
                    "VALUES (:t, 'spoken', :langs, 'seed', now() - (:i * interval '7 minutes'))"
                ),
                {
                    "t": f"{SAMPLES[i % len(SAMPLES)]} ({i + 1})",
                    "langs": ["hi", "en"] if i % 2 else ["en"],
                    "i": i // 3,  # groups of three share a timestamp to exercise tie-breaking
                },
            )
    await engine.dispose()
    print(f"Inserted {n} entries")


if __name__ == "__main__":
    asyncio.run(seed(int(sys.argv[1]) if len(sys.argv) > 1 else 20))
